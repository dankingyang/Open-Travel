#!/usr/bin/env python3
"""Validate provider exports and build comparable door-to-door plans."""

from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from travel_core import COST_FIELDS


TRANSPORT_KINDS = {"flight", "rail", "bus", "coach", "ferry", "transport"}
STAY_KINDS = {"stay", "hotel", "hostel", "guesthouse", "accommodation"}
ACCESS_KINDS = {"origin_access", "destination_egress"}
OFFER_KINDS = TRANSPORT_KINDS | STAY_KINDS | ACCESS_KINDS
SOURCE_TYPES = {
    "plugin",
    "mcp",
    "api",
    "web_search",
    "structured_web",
    "browser",
    "local",
}
PRICE_STATUSES = {"live", "recent", "estimated", "unavailable"}
COMPLETENESS_VALUES = {"complete", "partial", "unavailable"}
BAGGAGE_STATUSES = {"included", "not_included", "unknown", "not_returned"}
PROVIDER_ERROR_CODES = {
    "PROVIDER_CONTRACT_MISMATCH",
    "MARKET_LANGUAGE_MISMATCH",
    "DESTINATION_NOT_RESOLVED",
    "DESTINATION_MISMATCH",
    "NO_INVENTORY",
    "NO_ROUTE",
    "NOT_ON_SALE",
    "SUPPLIER_UNSUPPORTED",
    "PASSENGER_COUNT_MISMATCH",
    "RATE_LIMITED",
    "PROVIDER_TIMEOUT",
    "UPSTREAM_ERROR",
    "UNKNOWN_PROVIDER_ERROR",
}


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _number_or_none(value: Any, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a number or null")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a number or null") from exc
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{field} must be a finite non-negative number")
    return result


def _currency(value: Any, field: str) -> str:
    result = str(value or "").upper()
    if not re.fullmatch(r"[A-Z]{3}", result):
        raise ValueError(f"{field} must be a 3-letter currency code")
    return result


def _evidence(export: dict[str, Any], offer: dict[str, Any]) -> dict[str, Any]:
    evidence = deepcopy(offer.get("evidence") or {})
    if not isinstance(evidence, dict):
        raise ValueError("offer.evidence must be an object")
    defaults = {
        "provider": export.get("provider"),
        "source_type": export.get("source_type", "plugin"),
        "fetched_at": export.get("fetched_at"),
        "source_url": export.get("source_url"),
        "market": offer.get("market", export.get("market")),
        "currency": offer.get("currency", export.get("currency")),
        "price_status": export.get("price_status", "live"),
        "taxes_included": offer.get(
            "taxes_included", export.get("taxes_included")
        ),
        "baggage_status": offer.get(
            "baggage_status", export.get("baggage_status", "not_returned")
        ),
        "completeness": export.get("completeness", "partial"),
        "warnings": export.get("warnings", []),
    }
    for key, value in defaults.items():
        if key not in evidence and value is not None:
            evidence[key] = deepcopy(value)
    if not evidence.get("provider"):
        raise ValueError("provider export or offer evidence requires provider")
    if not evidence.get("fetched_at"):
        raise ValueError("provider export or offer evidence requires fetched_at")
    if not isinstance(evidence.get("warnings", []), list):
        raise ValueError("evidence.warnings must be an array")
    if evidence.get("source_type") not in SOURCE_TYPES:
        raise ValueError("evidence.source_type is unsupported")
    if evidence.get("price_status") not in PRICE_STATUSES:
        raise ValueError("evidence.price_status is unsupported")
    if evidence.get("completeness") not in COMPLETENESS_VALUES:
        raise ValueError("evidence.completeness is unsupported")
    if evidence.get("currency") is not None:
        evidence["currency"] = _currency(
            evidence["currency"], "evidence.currency"
        )
    if evidence.get("taxes_included") not in (True, False, None):
        raise ValueError("evidence.taxes_included must be true, false, or null")
    if evidence.get("baggage_status") not in BAGGAGE_STATUSES:
        raise ValueError("evidence.baggage_status is unsupported")
    return evidence


def _provider_errors(payload: dict[str, Any], source_label: str) -> list[dict[str, Any]]:
    errors = payload.get("errors") or []
    if not isinstance(errors, list):
        raise ValueError(f"{source_label}.errors must be an array")
    normalized = []
    for index, item in enumerate(errors):
        if not isinstance(item, dict):
            raise ValueError(f"{source_label}.errors[{index}] must be an object")
        code = str(item.get("code") or "UNKNOWN_PROVIDER_ERROR").upper()
        if code not in PROVIDER_ERROR_CODES:
            code = "UNKNOWN_PROVIDER_ERROR"
        normalized.append(
            {
                "provider": item.get("provider") or payload.get("provider", source_label),
                "code": code,
                "message": str(item.get("message") or ""),
                "request_id": item.get("request_id"),
                "retryable": item.get("retryable"),
                "context": deepcopy(item.get("context") or {}),
            }
        )
    return normalized


def normalize_export(payload: Any, *, source_label: str = "input") -> dict[str, Any]:
    """Validate the stable export contract used between MCP calls and the planner."""

    if isinstance(payload, list):
        payload = {"provider": source_label, "offers": payload}
    if not isinstance(payload, dict):
        raise ValueError(f"{source_label} must contain a JSON object or array")

    plans = payload.get("plans", [])
    offers = payload.get("offers", [])
    if not isinstance(plans, list) or not isinstance(offers, list):
        raise ValueError(f"{source_label}.plans and .offers must be arrays")

    normalized_offers = []
    for index, item in enumerate(offers):
        if not isinstance(item, dict):
            raise ValueError(f"{source_label}.offers[{index}] must be an object")
        offer = deepcopy(item)
        kind = str(offer.get("kind") or "").lower()
        if kind not in OFFER_KINDS:
            raise ValueError(
                f"{source_label}.offers[{index}].kind is unsupported: {kind!r}"
            )
        if not offer.get("id"):
            raise ValueError(f"{source_label}.offers[{index}] requires id")
        offer["kind"] = kind
        offer["evidence"] = _evidence(payload, offer)
        if "currency" in offer:
            offer["currency"] = _currency(
                offer["currency"], f"{source_label}.offers[{index}].currency"
            )
        normalized_offers.append(offer)

    normalized_plans = []
    for index, plan in enumerate(plans):
        if not isinstance(plan, dict) or not plan.get("id"):
            raise ValueError(f"{source_label}.plans[{index}] requires an id")
        normalized_plans.append(deepcopy(plan))

    return {
        "provider": payload.get("provider", source_label),
        "offers": normalized_offers,
        "plans": normalized_plans,
        "errors": _provider_errors(payload, source_label),
        "warnings": deepcopy(payload.get("warnings") or []),
    }


def _rate_for(
    base: str,
    quote: str,
    rates: dict[str, Any],
) -> float | None:
    if base == quote:
        return 1.0
    direct = rates.get(f"{base}/{quote}")
    if direct is not None:
        direct_value = _number_or_none(direct, f"fx_rates.{base}/{quote}")
        if direct_value is None or direct_value <= 0:
            raise ValueError(f"fx_rates.{base}/{quote} must be positive")
        return direct_value
    inverse = rates.get(f"{quote}/{base}")
    inverse_value = (
        _number_or_none(inverse, f"fx_rates.{quote}/{base}")
        if inverse is not None
        else None
    )
    if inverse_value and inverse_value > 0:
        return 1.0 / inverse_value
    if inverse_value is not None:
        raise ValueError(f"fx_rates.{quote}/{base} must be positive")
    return None


def _convert(
    value: Any,
    *,
    base: str,
    quote: str,
    rates: dict[str, Any],
    field: str,
) -> float | None:
    number = _number_or_none(value, field)
    if number is None:
        return None
    rate = _rate_for(base, quote, rates)
    if rate is None:
        raise ValueError(f"missing FX rate for {base}/{quote}")
    return round(number * rate, 2)


def _offer_costs(
    offer: dict[str, Any],
    *,
    target_currency: str,
    rates: dict[str, Any],
) -> tuple[dict[str, float | None], list[str]]:
    raw_costs = offer.get("costs") or {}
    if not isinstance(raw_costs, dict):
        raise ValueError(f"offer {offer['id']} costs must be an object")
    base = _currency(offer.get("currency", target_currency), f"offer {offer['id']} currency")
    costs: dict[str, float | None] = {}
    for key, value in raw_costs.items():
        if key not in COST_FIELDS:
            raise ValueError(f"offer {offer['id']} has unsupported cost field: {key}")
        costs[key] = _convert(
            value,
            base=base,
            quote=target_currency,
            rates=rates,
            field=f"offer {offer['id']}.costs.{key}",
        )
    required = offer.get("required_cost_fields") or list(raw_costs)
    if not isinstance(required, list):
        raise ValueError(f"offer {offer['id']} required_cost_fields must be an array")
    unknown = sorted(set(required) - set(COST_FIELDS))
    if unknown:
        raise ValueError(f"offer {offer['id']} has unsupported required costs: {unknown}")
    return costs, required


def _placeholder(kind: str, target_currency: str) -> dict[str, Any]:
    field = "origin_access" if kind == "origin_access" else "destination_egress"
    return {
        "kind": kind,
        "id": f"{kind}-unknown",
        "currency": target_currency,
        "costs": {field: None},
        "required_cost_fields": [field],
        "duration_minutes": 0,
        "transfers": 0,
        "walking_meters": 0,
        "comfort_score": 50,
        "connection": {},
        "evidence": {
            "provider": "planner",
            "source_type": "local",
            "fetched_at": None,
            "price_status": "unavailable",
            "completeness": "unavailable",
            "warnings": [f"{kind} was not supplied; its cost remains unknown."],
        },
    }


def _combine_one(
    transport: dict[str, Any],
    stay: dict[str, Any],
    origin_access: dict[str, Any],
    destination_egress: dict[str, Any],
    *,
    target_currency: str,
    rates: dict[str, Any],
) -> dict[str, Any]:
    parts = (transport, stay, origin_access, destination_egress)
    costs = {field: 0.0 for field in COST_FIELDS}
    cost_estimates: dict[str, dict[str, float]] = {}
    required: list[str] = []
    for part in parts:
        part_costs, part_required = _offer_costs(
            part, target_currency=target_currency, rates=rates
        )
        for field, value in part_costs.items():
            if value is None:
                costs[field] = None
            elif costs[field] is not None:
                costs[field] += value
        raw_estimates = part.get("cost_estimates") or {}
        if not isinstance(raw_estimates, dict):
            raise ValueError(f"offer {part['id']} cost_estimates must be an object")
        base = _currency(
            part.get("currency", target_currency),
            f"offer {part['id']} currency",
        )
        for field, raw_range in raw_estimates.items():
            if field not in COST_FIELDS or not isinstance(raw_range, dict):
                raise ValueError(
                    f"offer {part['id']} has invalid estimate for {field}"
                )
            minimum = _convert(
                raw_range.get("min"),
                base=base,
                quote=target_currency,
                rates=rates,
                field=f"offer {part['id']}.cost_estimates.{field}.min",
            )
            maximum = _convert(
                raw_range.get("max"),
                base=base,
                quote=target_currency,
                rates=rates,
                field=f"offer {part['id']}.cost_estimates.{field}.max",
            )
            if minimum is None or maximum is None or minimum > maximum:
                raise ValueError(
                    f"offer {part['id']} estimate for {field} requires min <= max"
                )
            current = cost_estimates.setdefault(field, {"min": 0.0, "max": 0.0})
            current["min"] += minimum
            current["max"] += maximum
        required.extend(part_required)

    duration = sum(
        _number_or_none(part.get("duration_minutes", 0), "duration_minutes") or 0
        for part in (transport, origin_access, destination_egress)
    )
    transfers = sum(
        _number_or_none(part.get("transfers", 0), "transfers") or 0
        for part in (transport, origin_access, destination_egress)
    )
    walking = sum(
        _number_or_none(part.get("walking_meters", 0), "walking_meters") or 0
        for part in (origin_access, destination_egress)
    )
    comfort_values = [
        _number_or_none(part.get("comfort_score"), "comfort_score")
        for part in parts
        if part.get("comfort_score") is not None
    ]
    comfort = (
        round(sum(value for value in comfort_values if value is not None) / len(comfort_values), 1)
        if comfort_values
        else 50.0
    )
    transport_connection = deepcopy(transport.get("connection") or {})
    destination_connection = destination_egress.get("connection") or {}
    for field in ("public_transport_last_time", "lodging_checkin_end"):
        if destination_connection.get(field) is not None:
            transport_connection[field] = destination_connection[field]

    return {
        "id": "--".join(part["id"] for part in parts),
        "title": f"{transport.get('title', transport['id'])} + {stay.get('title', stay['id'])}",
        "currency": target_currency,
        "costs": costs,
        "cost_estimates": {
            field: value
            for field, value in cost_estimates.items()
            if costs.get(field) is None
        },
        "required_cost_fields": sorted(set(required)),
        "duration_minutes": duration,
        "transfers": transfers,
        "walking_meters": walking,
        "comfort_score": comfort,
        "connection": transport_connection,
        "evidence": [deepcopy(part["evidence"]) for part in parts],
        "components": {
            "transport": transport["id"],
            "stay": stay["id"],
            "origin_access": origin_access["id"],
            "destination_egress": destination_egress["id"],
        },
    }


def build_candidate_plans(
    offers: Iterable[dict[str, Any]],
    *,
    target_currency: str,
    fx_rates: dict[str, Any] | None = None,
    max_per_kind: int = 20,
    max_plans: int = 200,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Build a bounded Cartesian set of transport/stay/access combinations."""

    target_currency = _currency(target_currency, "target_currency")
    if max_per_kind <= 0:
        raise ValueError("max_per_kind must be positive")
    if max_plans <= 0:
        raise ValueError("max_plans must be positive")
    rates = fx_rates or {}
    items = list(offers)
    transports = [item for item in items if item["kind"] in TRANSPORT_KINDS][:max_per_kind]
    stays = [item for item in items if item["kind"] in STAY_KINDS][:max_per_kind]
    origins = [item for item in items if item["kind"] == "origin_access"][:max_per_kind]
    destinations = [
        item for item in items if item["kind"] == "destination_egress"
    ][:max_per_kind]
    warnings: list[str] = []
    if not origins:
        origins = [_placeholder("origin_access", target_currency)]
        warnings.append("No origin-access offer: total cost will remain incomplete.")
    if not destinations:
        destinations = [_placeholder("destination_egress", target_currency)]
        warnings.append("No destination-egress offer: total cost will remain incomplete.")
    if not transports:
        warnings.append("No transport offer was available.")
    if not stays:
        warnings.append("No accommodation offer was available.")

    plans: list[dict[str, Any]] = []
    for transport in transports:
        for stay in stays:
            for origin in origins:
                for destination in destinations:
                    if len(plans) >= max_plans:
                        warnings.append(
                            f"Candidate combinations were capped at {max_plans}."
                        )
                        return plans, warnings
                    try:
                        plans.append(
                            _combine_one(
                                transport,
                                stay,
                                origin,
                                destination,
                                target_currency=target_currency,
                                rates=rates,
                            )
                        )
                    except ValueError as exc:
                        warnings.append(
                            f"Skipped {transport['id']} + {stay['id']}: {exc}"
                        )
    return plans, warnings
