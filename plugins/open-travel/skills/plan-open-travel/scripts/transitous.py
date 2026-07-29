#!/usr/bin/env python3
"""Transitous/MOTIS public transport adapter."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PLAN_URL = "https://api.transitous.org/api/v5/plan"
ATTRIBUTION_URL = "https://transitous.org/sources/"


class TransitousError(RuntimeError):
    """Transitous could not return usable structured data."""


def _fetched_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_contact(contact: str | None) -> str:
    value = (contact or os.getenv("TRAVEL_CONTACT") or "").strip()
    if not value:
        raise ValueError(
            "Transitous requires contact identification. Pass contact= or set "
            "TRAVEL_CONTACT to an email address or project URL."
        )
    if any(char in value for char in "\r\n"):
        raise ValueError("contact must be a single line")
    return value


def _place(value: str | tuple[float, float] | list[float], field: str) -> str:
    if isinstance(value, str):
        result = value.strip()
        if not result:
            raise ValueError(f"{field} must not be empty")
        return result
    if isinstance(value, (tuple, list)) and len(value) == 2:
        latitude, longitude = value
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} coordinates must be numbers") from exc
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError(f"{field} coordinates are out of range")
        return f"{latitude:.7f},{longitude:.7f}"
    raise ValueError(f"{field} must be a stop id or [latitude, longitude]")


def _request_json(
    url: str,
    params: dict[str, Any],
    timeout: float,
    user_agent: str,
) -> dict[str, Any]:
    source_url = f"{url}?{urlencode(params, doseq=True)}"
    request = Request(
        source_url,
        headers={"Accept": "application/json", "User-Agent": user_agent},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise TransitousError(f"HTTP {exc.code} from Transitous") from exc
    except (URLError, TimeoutError) as exc:
        raise TransitousError(f"Transitous network error: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise TransitousError("Transitous returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise TransitousError("Transitous returned an unexpected response")
    return payload


def _iso_datetime(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("time must be an ISO 8601 datetime with timezone") from exc
    if parsed.tzinfo is None:
        raise ValueError("time must include a timezone offset")
    return value


def _leg_place(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"name": None}
    return {
        key: value.get(key)
        for key in ("name", "stopId", "lat", "lon", "level")
        if value.get(key) is not None
    }


def _normalize_leg(leg: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": leg.get("mode"),
        "from": _leg_place(leg.get("from")),
        "to": _leg_place(leg.get("to")),
        "duration_seconds": leg.get("duration"),
        "distance_meters": leg.get("distance"),
        "start_time": leg.get("startTime"),
        "end_time": leg.get("endTime"),
        "scheduled_start_time": leg.get("scheduledStartTime"),
        "scheduled_end_time": leg.get("scheduledEndTime"),
        "realtime": leg.get("realTime"),
        "cancelled": leg.get("cancelled"),
        "operator": (leg.get("agency") or {}).get("name")
        if isinstance(leg.get("agency"), dict)
        else None,
        "route": (leg.get("route") or {}).get("shortName")
        if isinstance(leg.get("route"), dict)
        else leg.get("displayName"),
        "intermediate_stops": leg.get("intermediateStops") or [],
    }


def normalize_plan_response(
    payload: dict[str, Any],
    *,
    source_url: str,
) -> dict[str, Any]:
    itineraries = payload.get("itineraries")
    if itineraries is None and isinstance(payload.get("plan"), dict):
        itineraries = payload["plan"].get("itineraries")
    if not isinstance(itineraries, list):
        raise TransitousError("Transitous response has no itinerary list")

    offers: list[dict[str, Any]] = []
    for index, itinerary in enumerate(itineraries):
        if not isinstance(itinerary, dict):
            continue
        legs = [
            _normalize_leg(leg)
            for leg in itinerary.get("legs", [])
            if isinstance(leg, dict)
        ]
        walk_meters = sum(
            float(leg.get("distance_meters") or 0)
            for leg in legs
            if str(leg.get("mode") or "").upper() in {"WALK", "FOOT"}
        )
        warnings: list[str] = []
        if any(leg.get("cancelled") for leg in legs):
            warnings.append("At least one leg is marked cancelled.")
        if any(leg.get("realtime") is False for leg in legs):
            warnings.append("At least one leg has no real-time update.")
        offers.append(
            {
                "kind": "ground_route",
                "id": f"transitous-{index + 1}",
                "duration_minutes": round(float(itinerary.get("duration") or 0) / 60, 1),
                "transfers": itinerary.get("transfers"),
                "walking_meters": round(walk_meters),
                "start_time": itinerary.get("startTime"),
                "end_time": itinerary.get("endTime"),
                "legs": legs,
                "fare": None,
                "currency": None,
                "warnings": warnings,
                "evidence": {
                    "provider": "Transitous",
                    "source_type": "api",
                    "fetched_at": _fetched_at(),
                    "source_url": source_url,
                    "attribution_url": ATTRIBUTION_URL,
                    "price_status": "unavailable",
                    "completeness": "partial",
                    "warnings": [
                        "Transitous supplies routing, not a guaranteed fare quote.",
                        *warnings,
                    ],
                },
            }
        )
    return {
        "kind": "ground_routes",
        "status": "ok" if offers else "partial",
        "offers": offers,
        "warnings": [] if offers else ["Transitous returned no itineraries."],
        "attribution": {
            "label": "Transitous data sources",
            "url": ATTRIBUTION_URL,
        },
    }


def plan_routes(
    from_place: str | tuple[float, float] | list[float],
    to_place: str | tuple[float, float] | list[float],
    time: str,
    *,
    contact: str | None = None,
    arrive_by: bool = False,
    max_transfers: int | None = None,
    max_travel_time_minutes: int | None = None,
    transit_modes: list[str] | None = None,
    timeout: float = 15.0,
    fetch_json: Callable[[str, dict[str, Any], float, str], dict[str, Any]] = _request_json,
) -> dict[str, Any]:
    contact_value = _validate_contact(contact)
    if max_transfers is not None and max_transfers < 0:
        raise ValueError("max_transfers must be non-negative")
    if max_travel_time_minutes is not None and max_travel_time_minutes <= 0:
        raise ValueError("max_travel_time_minutes must be positive")

    params: dict[str, Any] = {
        "fromPlace": _place(from_place, "from_place"),
        "toPlace": _place(to_place, "to_place"),
        "time": _iso_datetime(time),
        "arriveBy": str(arrive_by).lower(),
        "detailedTransfers": "true",
    }
    if max_transfers is not None:
        params["maxTransfers"] = max_transfers
    if max_travel_time_minutes is not None:
        params["maxTravelTime"] = max_travel_time_minutes * 60
    if transit_modes:
        cleaned = [mode.upper() for mode in transit_modes if re.fullmatch(r"[A-Za-z_]+", mode)]
        if len(cleaned) != len(transit_modes):
            raise ValueError("transit_modes contains an invalid value")
        params["transitModes"] = ",".join(cleaned)

    user_agent = f"plan-open-travel/0.2 ({contact_value})"
    payload = fetch_json(PLAN_URL, params, timeout, user_agent)
    source_url = f"{PLAN_URL}?{urlencode(params, doseq=True)}"
    return normalize_plan_response(payload, source_url=source_url)


def _coordinates(value: str) -> list[float] | str:
    if "," not in value:
        return value
    parts = value.split(",")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("coordinates must be latitude,longitude")
    try:
        return [float(parts[0]), float(parts[1])]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("coordinates must be numbers") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Query Transitous public transport routes.")
    parser.add_argument("from_place", type=_coordinates)
    parser.add_argument("to_place", type=_coordinates)
    parser.add_argument("time", help="ISO 8601 datetime with timezone")
    parser.add_argument("--contact", help="Email or project URL for Transitous User-Agent")
    parser.add_argument("--arrive-by", action="store_true")
    parser.add_argument("--max-transfers", type=int)
    parser.add_argument("--max-travel-time-minutes", type=int)
    parser.add_argument("--transit-mode", action="append", dest="transit_modes")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    try:
        result = plan_routes(
            args.from_place,
            args.to_place,
            args.time,
            contact=args.contact,
            arrive_by=args.arrive_by,
            max_transfers=args.max_transfers,
            max_travel_time_minutes=args.max_travel_time_minutes,
            transit_modes=args.transit_modes,
            timeout=args.timeout,
        )
    except (TransitousError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
