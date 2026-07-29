from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = (
    ROOT
    / "plugins"
    / "open-travel"
    / "skills"
    / "plan-open-travel"
    / "scripts"
)
sys.path.insert(0, str(SCRIPT_DIR))
import public_data  # noqa: E402


class PublicDataTests(unittest.TestCase):
    def test_weather_forecast_normalizes_daily_rows(self):
        calls = []

        def fake_fetch(url, params, timeout):
            calls.append((url, params, timeout))
            if url == public_data.GEOCODING_URL:
                return {
                    "results": [
                        {
                            "name": "Tokyo",
                            "country": "Japan",
                            "country_code": "JP",
                            "admin1": "Tokyo",
                            "latitude": 35.68,
                            "longitude": 139.76,
                            "timezone": "Asia/Tokyo",
                            "population": 14000000,
                            "feature_code": "PPLC",
                        }
                    ]
                }
            return {
                "timezone": "Asia/Tokyo",
                "daily": {
                    "time": ["2026-08-01", "2026-08-02"],
                    "weather_code": [1, 61],
                    "temperature_2m_max": [31.2, 29.8],
                    "temperature_2m_min": [24.1, 23.9],
                    "precipitation_probability_max": [10, 70],
                },
            }

        result = public_data.weather_forecast(
            "东京",
            "2026-08-01",
            "2026-08-02",
            country_code="JP",
            query_name="Tokyo",
            fetch_json=fake_fetch,
            today=date(2026, 7, 29),
        )
        self.assertEqual(result["location"]["timezone"], "Asia/Tokyo")
        self.assertEqual(len(result["daily"]), 2)
        self.assertEqual(
            result["daily"][1]["precipitation_probability_max_percent"],
            70,
        )
        self.assertEqual(calls[0][0], public_data.GEOCODING_URL)
        self.assertEqual(calls[0][1]["countryCode"], "JP")
        self.assertEqual(calls[0][1]["name"], "Tokyo")
        self.assertEqual(calls[1][0], public_data.FORECAST_URL)

    def test_weather_prefers_populous_place_without_country_hint(self):
        def fake_fetch(url, params, timeout):
            if url == public_data.GEOCODING_URL:
                return {
                    "results": [
                        {
                            "name": "东京",
                            "country": "中国",
                            "country_code": "CN",
                            "latitude": 32.2,
                            "longitude": 119.2,
                            "population": 12000,
                            "feature_code": "PPL",
                        },
                        {
                            "name": "东京",
                            "country": "日本",
                            "country_code": "JP",
                            "latitude": 35.68,
                            "longitude": 139.76,
                            "population": 14000000,
                            "feature_code": "PPLC",
                        },
                    ]
                }
            return {
                "timezone": "Asia/Tokyo",
                "daily": {
                    "time": ["2026-08-01"],
                    "weather_code": [1],
                    "temperature_2m_max": [31],
                    "temperature_2m_min": [24],
                    "precipitation_probability_max": [10],
                },
            }

        result = public_data.weather_forecast(
            "东京",
            "2026-08-01",
            "2026-08-01",
            fetch_json=fake_fetch,
            today=date(2026, 7, 29),
        )
        self.assertEqual(result["location"]["country_code"], "JP")
        self.assertEqual(result["location"]["timezone"], "Asia/Tokyo")

    def test_exchange_rate_converts_amount(self):
        def fake_fetch(url, params, timeout):
            self.assertTrue(url.endswith("/rate/CNY/JPY"))
            return {
                "date": "2026-07-24",
                "base": "CNY",
                "quote": "JPY",
                "rate": 20.5,
            }

        result = public_data.exchange_rate(
            "100",
            "cny",
            "jpy",
            fetch_json=fake_fetch,
        )
        self.assertEqual(result["converted_amount"], 2050.0)
        self.assertEqual(result["evidence"]["price_status"], "recent")

    def test_exchange_rate_falls_back_to_ecb(self):
        def failed_frankfurter(url, params, timeout):
            raise public_data.ProviderError("timeout", code="TIMEOUT")

        ecb_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Envelope>
          <Cube>
            <Cube time="2026-07-28">
              <Cube currency="USD" rate="1.2"/>
              <Cube currency="CNY" rate="8.4"/>
            </Cube>
          </Cube>
        </Envelope>"""

        result = public_data.exchange_rate(
            "10",
            "USD",
            "CNY",
            fetch_json=failed_frankfurter,
            fetch_text=lambda url, timeout: ecb_xml,
        )
        self.assertEqual(result["rate"], 7.0)
        self.assertEqual(result["converted_amount"], 70.0)
        self.assertEqual(result["evidence"]["provider"], "European Central Bank")
        self.assertTrue(
            any("fallback" in warning for warning in result["evidence"]["warnings"])
        )

    def test_weather_outside_window_returns_requery_dates(self):
        result = public_data.weather_forecast(
            "Langkawi",
            "2026-08-20",
            "2026-08-22",
            today=date(2026, 7, 29),
        )
        self.assertEqual(result["daily"], [])
        self.assertEqual(
            result["availability"]["status"], "outside_forecast_window"
        )
        self.assertEqual(
            result["availability"]["earliest_query_date"], "2026-08-05"
        )
        self.assertEqual(
            result["availability"]["suggested_recheck_date"], "2026-08-13"
        )

    def test_unknown_location_is_reported(self):
        def fake_fetch(url, params, timeout):
            return {"results": []}

        with self.assertRaisesRegex(public_data.ProviderError, "could not resolve"):
            public_data.weather_forecast(
                "不存在地点",
                "2026-08-01",
                "2026-08-02",
                fetch_json=fake_fetch,
                today=date(2026, 7, 29),
            )

    def test_rejects_unsafe_currency_code(self):
        with self.assertRaisesRegex(ValueError, "3-letter"):
            public_data.exchange_rate("100", "CNY/../../", "JPY")


if __name__ == "__main__":
    unittest.main()
