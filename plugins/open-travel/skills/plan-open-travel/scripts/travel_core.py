"""Deterministic complete-cost, risk, and plan-selection logic."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import math
from typing import Any, Iterable


COST_FIELDS = (
    "transport_fare",
    "taxes",
    "baggage",
    "seat",
    "origin_access",
    "destination_egress",
    "stay",
    "stay_taxes",
    "cleaning",
    "city_tax",
    "late_transport",
    "extra_nights",
    "other",
)

DEFAULT_REQUIRED_COST_FIELDS = (
    "transport_fare",
    "taxes",
    "origin_access",
    "destination_egress",
    "stay",
)


@dataclass(frozen=True)
class Risk:
    code: str
    points: int
    message: str


def _decimal(value: Any, field: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a number, not boolean")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be a finite non-negative number") from exc
    if not result.is_finite() or result < 0:
        raise ValueError(f"{field} must be a finite non-negative number")
    return result


def _number(value: Any, field: str, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a number, not boolean")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a number") from exc
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{field} must be a finite non-negative number")
    return result


def calculate_cost(plan: dict[str, Any]) -> dict[str, Any]:
    costs = plan.get("costs") or {}
    if not isinstance(costs, dict):
        raise ValueError("costs must be an object")

    required = plan.get("required_cost_fields", DEFAULT_REQUIRED_COST_FIELDS)
    if not isinstance(required, (list, tuple)):
        raise ValueError("required_cost_fields must be an array")
    unknown_required = sorted(set(required) - set(COST_FIELDS))
    if unknown_required:
        raise ValueError(f"unknown required cost fields: {', '.join(unknown_required)}")

    normalized: dict[str, Decimal | None] = {}
    for field in COST_FIELDS:
        normalized[field] = _decimal(costs.get(field, 0), f"costs.{field}")

    missing = sorted(field for field in required if normalized.get(field) is None)
    known_subtotal = sum(
        (value for value in normalized.values() if value is not None),
        Decimal("0"),
    )
    raw_estimates = plan.get("cost_estimates") or {}
    if not isinstance(raw_estimates, dict):
        raise ValueError("cost_estimates must be an object")
    unknown_estimate_fields = sorted(set(raw_estimates) - set(COST_FIELDS))
    if unknown_estimate_fields:
        raise ValueError(
            f"unknown cost estimate fields: {', '.join(unknown_estimate_fields)}"
        )
    estimates: dict[str, dict[str, float]] = {}
    for field in missing:
        raw_range = raw_estimates.get(field)
        if raw_range is None:
            continue
        if not isinstance(raw_range, dict):
            raise ValueError(f"cost_estimates.{field} must be an object")
        minimum = _decimal(raw_range.get("min"), f"cost_estimates.{field}.min")
        maximum = _decimal(raw_range.get("max"), f"cost_estimates.{field}.max")
        if minimum is None or maximum is None:
            raise ValueError(f"cost_estimates.{field} requires min and max")
        if minimum > maximum:
            raise ValueError(f"cost_estimates.{field}.min must not exceed max")
        estimates[field] = {"min": float(minimum), "max": float(maximum)}

    estimated_range = None
    if missing and all(field in estimates for field in missing):
        estimated_range = {
            "min": float(
                known_subtotal
                + sum(Decimal(str(estimates[field]["min"])) for field in missing)
            ),
            "max": float(
                known_subtotal
                + sum(Decimal(str(estimates[field]["max"])) for field in missing)
            ),
        }
    return {
        "currency": plan.get("currency", "CNY"),
        "known_subtotal": float(known_subtotal),
        "total": None if missing else float(known_subtotal),
        "complete": not missing,
        "missing_fields": missing,
        "estimated_range": estimated_range,
        "estimated_fields": sorted(estimates),
        "breakdown": {
            field: None if value is None else float(value)
            for field, value in normalized.items()
        },
    }


def _minutes(time_value: Any) -> int | None:
    if not time_value or not isinstance(time_value, str) or ":" not in time_value:
        return None
    try:
        hour, minute = (int(part) for part in time_value.split(":", 1))
    except ValueError:
        return None
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return None
    return hour * 60 + minute


def detect_risks(plan: dict[str, Any], cost: dict[str, Any]) -> list[Risk]:
    connection = plan.get("connection") or {}
    evidence = plan.get("evidence") or []
    risks: list[Risk] = []

    rules = (
        ("self_transfer", 25, "self-transfer", "自助转机"),
        ("separate_tickets", 25, "separate-tickets", "分开出票"),
        ("airport_change", 25, "airport-change", "需要更换机场"),
        ("station_change", 15, "station-change", "需要跨车站换乘"),
        ("checked_bag_reclaim", 10, "bag-reclaim", "中转时需提取并重新托运行李"),
    )
    for field, points, code, message in rules:
        if connection.get(field) is True:
            risks.append(Risk(code, points, message))

    connection_minutes = connection.get("connection_minutes")
    if connection_minutes is not None:
        actual = _number(connection_minutes, "connection.connection_minutes")
        scope = connection.get("connection_scope", "domestic")
        threshold = 120 if scope == "international" else 60
        if actual < threshold:
            risks.append(
                Risk(
                    "short-connection",
                    20,
                    f"换乘仅 {actual:g} 分钟，低于 {threshold} 分钟基准",
                )
            )

    departure = _minutes(connection.get("departure_local_time"))
    if departure is not None and (departure < 6 * 60 or departure >= 23 * 60):
        risks.append(Risk("red-eye", 10, "红眼或过早出发"))

    arrival = _minutes(connection.get("arrival_local_time"))
    last_transit = _minutes(connection.get("public_transport_last_time"))
    if arrival is not None and last_transit is not None and arrival > last_transit:
        risks.append(Risk("after-last-transit", 20, "抵达晚于公共交通末班时间"))

    checkin_end = _minutes(connection.get("lodging_checkin_end"))
    if arrival is not None and checkin_end is not None and arrival > checkin_end:
        risks.append(Risk("after-checkin", 15, "抵达晚于住宿常规入住截止时间"))

    if not cost["complete"]:
        risks.append(
            Risk(
                "missing-costs",
                30,
                "缺少必要费用：" + "、".join(cost["missing_fields"]),
            )
        )

    complete_evidence = [
        item
        for item in evidence
        if isinstance(item, dict) and item.get("completeness") == "complete"
    ]
    if len(complete_evidence) == 1:
        risks.append(Risk("single-source", 8, "关键价格只有单一完整来源"))
    if evidence and not complete_evidence:
        risks.append(Risk("partial-evidence", 15, "没有完整的价格证据"))

    return risks


def _constraint_failures(
    plan: dict[str, Any],
    cost: dict[str, Any],
    risks: list[Risk],
    constraints: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    risk_codes = {risk.code for risk in risks}

    max_cost = constraints.get("max_total_cost")
    if max_cost is not None:
        limit = _number(max_cost, "hard_constraints.max_total_cost")
        if cost["total"] is None:
            failures.append("总价不完整，无法证明满足预算上限")
        elif cost["total"] > limit:
            failures.append(f"完整总价 {cost['total']:g} 超过上限 {limit:g}")

    numeric_constraints = (
        ("max_duration_minutes", "duration_minutes", "总耗时"),
        ("max_transfers", "transfers", "换乘次数"),
    )
    for constraint_name, plan_field, label in numeric_constraints:
        if constraints.get(constraint_name) is not None:
            limit = _number(
                constraints[constraint_name],
                f"hard_constraints.{constraint_name}",
            )
            actual = _number(plan.get(plan_field), plan_field)
            if actual > limit:
                failures.append(f"{label} {actual:g} 超过上限 {limit:g}")

    disallowed = (
        ("disallow_self_transfer", "self-transfer", "不接受自助转机"),
        ("disallow_separate_tickets", "separate-tickets", "不接受分开出票"),
        ("disallow_airport_change", "airport-change", "不接受更换机场"),
        ("disallow_red_eye", "red-eye", "不接受红眼或过早出发"),
    )
    for constraint_name, risk_code, message in disallowed:
        if constraints.get(constraint_name) is True and risk_code in risk_codes:
            failures.append(message)

    return failures


def evaluate_plan(plan: dict[str, Any], constraints: dict[str, Any]) -> dict[str, Any]:
    if not plan.get("id"):
        raise ValueError("each plan requires a non-empty id")
    cost = calculate_cost(plan)
    risks = detect_risks(plan, cost)
    failures = _constraint_failures(plan, cost, risks, constraints)
    return {
        **plan,
        "cost": cost,
        "risk_points": sum(risk.points for risk in risks),
        "risks": [risk.__dict__ for risk in risks],
        "eligible": not failures,
        "constraint_failures": failures,
        "duration_minutes": _number(plan.get("duration_minutes"), "duration_minutes"),
        "transfers": _number(plan.get("transfers"), "transfers"),
        "walking_meters": _number(plan.get("walking_meters"), "walking_meters"),
        "comfort_score": min(
            100.0,
            _number(plan.get("comfort_score"), "comfort_score", 50.0),
        ),
    }


def _dominates(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_total = left["cost"]["total"]
    right_total = right["cost"]["total"]
    if left_total is None or right_total is None:
        return False
    no_worse = (
        left_total <= right_total
        and left["duration_minutes"] <= right["duration_minutes"]
        and left["risk_points"] <= right["risk_points"]
        and left["comfort_score"] >= right["comfort_score"]
    )
    strictly_better = (
        left_total < right_total
        or left["duration_minutes"] < right["duration_minutes"]
        or left["risk_points"] < right["risk_points"]
        or left["comfort_score"] > right["comfort_score"]
    )
    return no_worse and strictly_better


def pareto_frontier(plans: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [
        plan
        for plan in plans
        if plan["eligible"] and plan["cost"]["total"] is not None
    ]
    return [
        candidate
        for candidate in candidates
        if not any(
            _dominates(other, candidate)
            for other in candidates
            if other["id"] != candidate["id"]
        )
    ]


def _normalize(value: float, values: list[float]) -> float:
    low, high = min(values), max(values)
    if high == low:
        return 0.0
    return (value - low) / (high - low)


def _balanced_scores(frontier: list[dict[str, Any]]) -> dict[str, float]:
    totals = [plan["cost"]["total"] for plan in frontier]
    durations = [plan["duration_minutes"] for plan in frontier]
    risk_points = [float(plan["risk_points"]) for plan in frontier]
    discomforts = [100.0 - plan["comfort_score"] for plan in frontier]
    return {
        plan["id"]: (
            0.45 * _normalize(plan["cost"]["total"], totals)
            + 0.25 * _normalize(plan["duration_minutes"], durations)
            + 0.20 * _normalize(float(plan["risk_points"]), risk_points)
            + 0.10
            * _normalize(100.0 - plan["comfort_score"], discomforts)
        )
        for plan in frontier
    }


def select_representatives(
    frontier: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    if not frontier:
        return {}

    balanced_scores = _balanced_scores(frontier)
    selected: dict[str, dict[str, Any]] = {
        "recommended": min(
            frontier,
            key=lambda plan: (
                balanced_scores[plan["id"]],
                plan["risk_points"],
                plan["cost"]["total"],
            ),
        )
    }
    selected["lowest-cost"] = min(
        frontier,
        key=lambda plan: (
            plan["cost"]["total"],
            plan["risk_points"],
            plan["duration_minutes"],
        ),
    )
    selected["fastest"] = min(
        frontier,
        key=lambda plan: (
            plan["duration_minutes"],
            plan["risk_points"],
            plan["cost"]["total"],
        ),
    )
    selected["low-hassle"] = min(
        frontier,
        key=lambda plan: (
            plan["transfers"],
            plan["risk_points"],
            plan["walking_meters"],
            plan["duration_minutes"],
            plan["cost"]["total"],
        ),
    )
    selected["comfort"] = min(
        frontier,
        key=lambda plan: (
            plan["risk_points"],
            -plan["comfort_score"],
            plan["transfers"],
            plan["duration_minutes"],
            plan["cost"]["total"],
        ),
    )
    return selected


def build_options(
    frontier: list[dict[str, Any]],
    selected: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not frontier:
        return []

    role_order = ("recommended", "lowest-cost", "fastest", "low-hassle", "comfort")
    by_id: dict[str, dict[str, Any]] = {}
    ordered_ids: list[str] = []
    for role in role_order:
        plan = selected[role]
        if plan["id"] not in by_id:
            by_id[plan["id"]] = {"plan": plan, "badges": []}
            ordered_ids.append(plan["id"])
        by_id[plan["id"]]["badges"].append(role)

    if len(ordered_ids) < min(3, len(frontier)):
        balanced_scores = _balanced_scores(frontier)
        remaining = sorted(
            (plan for plan in frontier if plan["id"] not in by_id),
            key=lambda plan: (
                balanced_scores[plan["id"]],
                plan["risk_points"],
                plan["cost"]["total"],
            ),
        )
        for plan in remaining:
            by_id[plan["id"]] = {"plan": plan, "badges": []}
            ordered_ids.append(plan["id"])
            if len(ordered_ids) >= min(3, len(frontier)):
                break

    options: list[dict[str, Any]] = []
    for index, plan_id in enumerate(ordered_ids[:5]):
        item = by_id[plan_id]
        plan = item["plan"]
        options.append(
            {
                "option_id": chr(ord("A") + index),
                "id": plan["id"],
                "title": plan.get("title", plan["id"]),
                "badges": item["badges"],
                "total": plan["cost"]["total"],
                "currency": plan["cost"]["currency"],
                "duration_minutes": plan["duration_minutes"],
                "transfers": plan["transfers"],
                "risk_points": plan["risk_points"],
                "comfort_score": plan["comfort_score"],
            }
        )
    return options


def build_estimated_options(plans: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build a separate, non-ranked view of incomplete plans with full ranges."""

    candidates = [
        plan
        for plan in plans
        if plan["eligible"]
        and not plan["cost"]["complete"]
        and plan["cost"]["estimated_range"] is not None
    ]
    candidates.sort(
        key=lambda plan: (
            (
                plan["cost"]["estimated_range"]["min"]
                + plan["cost"]["estimated_range"]["max"]
            )
            / 2,
            plan["risk_points"],
            plan["duration_minutes"],
        )
    )
    return [
        {
            "option_id": f"R{index}",
            "id": plan["id"],
            "title": plan.get("title", plan["id"]),
            "known_subtotal": plan["cost"]["known_subtotal"],
            "estimated_range": plan["cost"]["estimated_range"],
            "estimated_fields": plan["cost"]["estimated_fields"],
            "missing_fields": plan["cost"]["missing_fields"],
            "currency": plan["cost"]["currency"],
            "duration_minutes": plan["duration_minutes"],
            "risk_points": plan["risk_points"],
            "status": "estimated-reference",
        }
        for index, plan in enumerate(candidates[:5], start=1)
    ]


def evaluate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    plans = payload.get("plans")
    if not isinstance(plans, list) or not plans:
        raise ValueError("payload.plans must be a non-empty array")
    request = payload.get("request") or {}
    constraints = request.get("hard_constraints") or {}
    if not isinstance(constraints, dict):
        raise ValueError("request.hard_constraints must be an object")

    evaluated = [evaluate_plan(plan, constraints) for plan in plans]
    identifiers = [plan["id"] for plan in evaluated]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("plan ids must be unique")

    frontier = pareto_frontier(evaluated)
    selected = select_representatives(frontier)
    options = build_options(frontier, selected)
    estimated_options = build_estimated_options(evaluated)
    return {
        "request": request,
        "selected": {
            role: {
                "id": plan["id"],
                "title": plan.get("title", plan["id"]),
                "total": plan["cost"]["total"],
                "currency": plan["cost"]["currency"],
                "duration_minutes": plan["duration_minutes"],
                "risk_points": plan["risk_points"],
                "comfort_score": plan["comfort_score"],
            }
            for role, plan in selected.items()
        },
        "options": options,
        "estimated_options": estimated_options,
        "pareto_ids": [plan["id"] for plan in frontier],
        "plans": evaluated,
    }
