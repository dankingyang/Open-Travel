#!/usr/bin/env python3
"""Keyless weather and central-bank reference FX client."""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FRANKFURTER_URL = "https://api.frankfurter.dev/v2"
ECB_DAILY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
FORECAST_DAYS = 16
USER_AGENT = "plan-open-travel/0.1 (personal travel planning)"


class ProviderError(RuntimeError):
    """A public data provider could not return usable structured data."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "UPSTREAM_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}

    def __str__(self) -> str:
        return f"[{self.code}] {super().__str__()}"


def _request_bytes(url: str, timeout: float, *, attempts: int = 2) -> bytes:
    request = Request(
        url,
        headers={"Accept": "*/*", "User-Agent": USER_AGENT},
    )
    last_error: ProviderError | None = None
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as exc:
            code = "RATE_LIMITED" if exc.code == 429 else "HTTP_ERROR"
            last_error = ProviderError(
                f"HTTP {exc.code} from {url}",
                code=code,
                details={"status": exc.code, "url": url},
            )
            if exc.code < 500 and exc.code != 429:
                break
        except (TimeoutError, socket.timeout) as exc:
            last_error = ProviderError(
                f"request timed out: {url}",
                code="TIMEOUT",
                details={"url": url},
            )
        except URLError as exc:
            reason = getattr(exc, "reason", None)
            code = "DNS_ERROR" if isinstance(reason, socket.gaierror) else "NETWORK_ERROR"
            last_error = ProviderError(
                f"network error from {url}: {reason or exc}",
                code=code,
                details={"url": url},
            )
        if attempt + 1 < attempts:
            time.sleep(0.2 * (attempt + 1))
    raise last_error or ProviderError(
        f"request failed: {url}",
        code="UPSTREAM_UNAVAILABLE",
    )


def _request_json(url: str, params: dict[str, Any], timeout: float) -> dict[str, Any]:
    query = urlencode(params, doseq=True)
    request_url = f"{url}?{query}" if query else url
    try:
        payload = json.loads(_request_bytes(request_url, timeout).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ProviderError(
            f"invalid JSON from {url}",
            code="INVALID_RESPONSE",
            details={"url": request_url},
        ) from exc
    if not isinstance(payload, (dict, list)):
        raise ProviderError(
            f"unexpected response from {url}",
            code="INVALID_RESPONSE",
            details={"url": request_url},
        )
    return payload


def _request_text(url: str, timeout: float) -> str:
    try:
        return _request_bytes(url, timeout).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProviderError(
            f"invalid text response from {url}",
            code="INVALID_RESPONSE",
            details={"url": url},
        ) from exc


def _source_url(url: str, params: dict[str, Any]) -> str:
    query = urlencode(params, doseq=True)
    return f"{url}?{query}" if query else url


def _fetched_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must use YYYY-MM-DD") from exc


def weather_forecast(
    place: str,
    start_date: str,
    end_date: str,
    *,
    language: str = "zh",
    country_code: str | None = None,
    query_name: str | None = None,
    timeout: float = 10.0,
    fetch_json: Callable[[str, dict[str, Any], float], Any] = _request_json,
    today: date | None = None,
) -> dict[str, Any]:
    if len(place.strip()) < 2:
        raise ValueError("place must contain at least two characters")
    start = _iso_date(start_date, "start_date")
    end = _iso_date(end_date, "end_date")
    if end < start:
        raise ValueError("end_date must not be earlier than start_date")
    today_value = today or date.today()
    latest_forecast_date = today_value + timedelta(days=FORECAST_DAYS - 1)
    earliest_query_date = start - timedelta(days=FORECAST_DAYS - 1)
    recheck_date = start - timedelta(days=7)
    if start > latest_forecast_date:
        return {
            "kind": "weather_forecast",
            "location": {"name": place},
            "daily": [],
            "availability": {
                "status": "outside_forecast_window",
                "requested_start_date": start.isoformat(),
                "latest_forecast_date": latest_forecast_date.isoformat(),
                "earliest_query_date": earliest_query_date.isoformat(),
                "suggested_recheck_date": recheck_date.isoformat(),
            },
            "evidence": {
                "provider": "Open-Meteo",
                "source_type": "api",
                "fetched_at": _fetched_at(),
                "source_url": None,
                "completeness": "unavailable",
                "warnings": [
                    "Requested dates are outside the rolling forecast window; "
                    "climate averages were not substituted."
                ],
            },
        }
    if country_code is not None:
        country_code = country_code.upper()
        if not re.fullmatch(r"[A-Z]{2}", country_code):
            raise ValueError("country_code must be a 2-letter ISO code")
    if query_name is not None and len(query_name.strip()) < 2:
        raise ValueError("query_name must contain at least two characters")

    geocode_params = {
        "name": (query_name or place).strip(),
        "count": 10,
        "language": language.lower(),
        "format": "json",
    }
    if country_code:
        geocode_params["countryCode"] = country_code
    geocoded = fetch_json(GEOCODING_URL, geocode_params, timeout)
    results = geocoded.get("results", []) if isinstance(geocoded, dict) else []
    if not results:
        raise ProviderError(f"Open-Meteo could not resolve location: {place}")
    place_rank = {
        "PPLC": 5,
        "PPLA": 4,
        "PPLA2": 3,
        "PPLA3": 2,
        "PPL": 1,
    }
    location = max(
        results,
        key=lambda item: (
            int(item.get("population") or 0),
            place_rank.get(item.get("feature_code"), 0),
        ),
    )

    requested_end = end
    end = min(end, latest_forecast_date)
    forecast_params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "daily": (
            "weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max"
        ),
        "timezone": "auto",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }
    forecast = fetch_json(FORECAST_URL, forecast_params, timeout)
    daily = forecast.get("daily") if isinstance(forecast, dict) else None
    if not isinstance(daily, dict) or not daily.get("time"):
        reason = forecast.get("reason") if isinstance(forecast, dict) else None
        raise ProviderError(reason or "Open-Meteo returned no daily forecast")

    keys = (
        "time",
        "weather_code",
        "temperature_2m_max",
        "temperature_2m_min",
        "precipitation_probability_max",
    )
    lengths = {len(daily.get(key, [])) for key in keys}
    if len(lengths) != 1:
        raise ProviderError("Open-Meteo daily arrays have inconsistent lengths")
    rows = [
        {
            "date": daily["time"][index],
            "weather_code": daily["weather_code"][index],
            "temperature_max_c": daily["temperature_2m_max"][index],
            "temperature_min_c": daily["temperature_2m_min"][index],
            "precipitation_probability_max_percent": daily[
                "precipitation_probability_max"
            ][index],
        }
        for index in range(len(daily["time"]))
    ]
    return {
        "kind": "weather_forecast",
        "location": {
            "name": location.get("name"),
            "country": location.get("country"),
            "country_code": location.get("country_code"),
            "admin1": location.get("admin1"),
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "timezone": forecast.get("timezone") or location.get("timezone"),
        },
        "daily": rows,
        "availability": {
            "status": "partial" if requested_end > end else "available",
            "requested_end_date": requested_end.isoformat(),
            "available_through": end.isoformat(),
            "suggested_recheck_date": recheck_date.isoformat(),
        },
        "evidence": {
            "provider": "Open-Meteo",
            "source_type": "api",
            "fetched_at": _fetched_at(),
            "source_url": _source_url(FORECAST_URL, forecast_params),
            "location_source_url": _source_url(GEOCODING_URL, geocode_params),
            "completeness": "partial" if requested_end > end else "complete",
            "warnings": (
                [
                    "Forecast was clipped to the provider's current rolling "
                    "window; re-query the remaining dates later."
                ]
                if requested_end > end
                else []
            ),
        },
    }


def _default_cache_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME")
    if base:
        return Path(base) / "OpenTravel" / "cache" / "fx.json"
    return Path.home() / ".cache" / "open-travel" / "fx.json"


def _load_cache(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_cache(path: Path, payload: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass


def _ecb_rate(xml_text: str, base: str, quote_currency: str) -> tuple[Decimal, str]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ProviderError(
            "ECB returned invalid XML",
            code="INVALID_RESPONSE",
        ) from exc
    dated_cube = next(
        (item for item in root.iter() if item.attrib.get("time")),
        None,
    )
    if dated_cube is None:
        raise ProviderError("ECB returned no dated rates", code="INVALID_RESPONSE")
    rates = {"EUR": Decimal("1")}
    for item in dated_cube:
        currency = item.attrib.get("currency")
        value = item.attrib.get("rate")
        if currency and value:
            rates[currency] = Decimal(value)
    if base not in rates or quote_currency not in rates:
        raise ProviderError(
            f"ECB does not publish {base}/{quote_currency}",
            code="UPSTREAM_UNAVAILABLE",
        )
    return rates[quote_currency] / rates[base], dated_cube.attrib["time"]


def exchange_rate(
    amount: str | int | float | Decimal,
    base: str,
    quote_currency: str,
    *,
    timeout: float = 10.0,
    fetch_json: Callable[[str, dict[str, Any], float], Any] = _request_json,
    fetch_text: Callable[[str, float], str] = _request_text,
    cache_path: str | Path | None = None,
) -> dict[str, Any]:
    base = base.upper()
    quote_currency = quote_currency.upper()
    if not re.fullmatch(r"[A-Z]{3}", base):
        raise ValueError("base must be a 3-letter currency code")
    if not re.fullmatch(r"[A-Z]{3}", quote_currency):
        raise ValueError("quote must be a 3-letter currency code")
    try:
        decimal_amount = Decimal(str(amount))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("amount must be a finite non-negative number") from exc
    if not decimal_amount.is_finite() or decimal_amount < 0:
        raise ValueError("amount must be a finite non-negative number")

    use_cache = fetch_json is _request_json
    resolved_cache_path = Path(cache_path) if cache_path else _default_cache_path()
    cache = _load_cache(resolved_cache_path) if use_cache else {}
    cache_key = f"{base}/{quote_currency}"
    cached = cache.get(cache_key)
    today_text = date.today().isoformat()
    if isinstance(cached, dict) and cached.get("cached_on") == today_text:
        rate = Decimal(str(cached["rate"]))
        rate_date = cached.get("rate_date")
        provider = cached.get("provider", "cached reference rate")
        source_url = cached.get("source_url")
        warnings = ["Loaded from today's local central-bank reference-rate cache."]
    else:
        url = f"{FRANKFURTER_URL}/rate/{quote(base)}/{quote(quote_currency)}"
        warnings = []
        try:
            payload = fetch_json(url, {}, timeout)
            if not isinstance(payload, dict) or payload.get("rate") is None:
                raise ProviderError(
                    "Frankfurter returned no exchange rate",
                    code="INVALID_RESPONSE",
                )
            rate = Decimal(str(payload["rate"]))
            rate_date = payload.get("date")
            provider = "Frankfurter"
            source_url = url
        except (ProviderError, InvalidOperation, ValueError) as primary_error:
            try:
                rate, rate_date = _ecb_rate(
                    fetch_text(ECB_DAILY_URL, timeout),
                    base,
                    quote_currency,
                )
                provider = "European Central Bank"
                source_url = ECB_DAILY_URL
                warnings.append(
                    f"Frankfurter unavailable; used ECB fallback: {primary_error}"
                )
            except ProviderError as fallback_error:
                raise ProviderError(
                    "both Frankfurter and ECB reference-rate sources failed",
                    code="UPSTREAM_UNAVAILABLE",
                    details={
                        "primary": str(primary_error),
                        "fallback": str(fallback_error),
                    },
                ) from fallback_error
        if not rate.is_finite() or rate <= 0:
            raise ProviderError(
                "reference provider returned an invalid exchange rate",
                code="INVALID_RESPONSE",
            )
        if use_cache:
            cache[cache_key] = {
                "rate": str(rate),
                "rate_date": rate_date,
                "provider": provider,
                "source_url": source_url,
                "cached_on": today_text,
            }
            _save_cache(resolved_cache_path, cache)

    converted = decimal_amount * rate
    return {
        "kind": "exchange_rate",
        "amount": float(decimal_amount),
        "base": base,
        "quote": quote_currency,
        "rate": float(rate),
        "converted_amount": float(converted),
        "rate_date": rate_date,
        "evidence": {
            "provider": provider,
            "source_type": "api",
            "fetched_at": _fetched_at(),
            "source_url": source_url,
            "price_status": "recent",
            "completeness": "complete",
            "warnings": warnings
            + [
                "Daily reference rate; card, bank, or cash exchange spreads are excluded."
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Query keyless supporting travel data.")
    parser.add_argument("--timeout", type=float, default=10.0)
    commands = parser.add_subparsers(dest="command", required=True)

    weather = commands.add_parser("weather", help="Get an Open-Meteo daily forecast")
    weather.add_argument("place")
    weather.add_argument("start_date")
    weather.add_argument("end_date")
    weather.add_argument("--language", default="zh")
    weather.add_argument("--country-code")
    weather.add_argument("--query-name")

    fx = commands.add_parser("fx", help="Convert using a Frankfurter daily rate")
    fx.add_argument("amount")
    fx.add_argument("base")
    fx.add_argument("quote")

    args = parser.parse_args()
    try:
        if args.command == "weather":
            result = weather_forecast(
                args.place,
                args.start_date,
                args.end_date,
                language=args.language,
                country_code=args.country_code,
                query_name=args.query_name,
                timeout=args.timeout,
            )
        else:
            result = exchange_rate(
                args.amount,
                args.base,
                args.quote,
                timeout=args.timeout,
            )
    except (ProviderError, ValueError, KeyError) as exc:
        if isinstance(exc, ProviderError):
            diagnostic = {
                "error": exc.code,
                "message": str(exc),
                "details": exc.details,
            }
            print(json.dumps(diagnostic, ensure_ascii=False), file=sys.stderr)
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
