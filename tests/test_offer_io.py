from __future__ import annotations

import math
import sys
import unittest
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
import offer_io  # noqa: E402
import travel_core  # noqa: E402


def export_with(offers):
    return {
        "provider": "Trip.com",
        "source_type": "plugin",
        "fetched_at": "2026-07-29T12:00:00+08:00",
        "source_url": "https://example.test/search",
        "price_status": "live",
        "completeness": "complete",
        "warnings": [],
        "offers": offers,
    }


class OfferIoTests(unittest.TestCase):
    def test_plugin_evidence_and_seller_are_preserved(self):
        normalized = offer_io.normalize_export(
            export_with(
                [
                    {
                        "kind": "hotel",
                        "id": "hotel-1",
                        "currency": "CNY",
                        "seller": "Hotel direct",
                        "costs": {"stay": 800},
                        "required_cost_fields": ["stay"],
                    }
                ]
            )
        )
        offer = normalized["offers"][0]
        self.assertEqual(offer["seller"], "Hotel direct")
        self.assertEqual(offer["evidence"]["source_type"], "plugin")
        self.assertEqual(offer["evidence"]["currency"], "CNY")
        self.assertEqual(offer["evidence"]["baggage_status"], "not_returned")

    def test_partial_offers_and_structured_errors_are_both_preserved(self):
        payload = export_with(
            [
                {
                    "kind": "hotel",
                    "id": "hotel-1",
                    "currency": "CNY",
                    "costs": {"stay": 800},
                }
            ]
        )
        payload["errors"] = [
            {
                "code": "DESTINATION_NOT_RESOLVED",
                "message": "Unknown city",
                "request_id": "request-123",
                "context": {"query": "Melaka"},
            }
        ]
        normalized = offer_io.normalize_export(payload)
        self.assertEqual(len(normalized["offers"]), 1)
        self.assertEqual(
            normalized["errors"][0]["code"], "DESTINATION_NOT_RESOLVED"
        )
        self.assertEqual(normalized["errors"][0]["request_id"], "request-123")

    def test_trivago_diagnostic_codes_are_preserved(self):
        payload = export_with([])
        payload["errors"] = [
            {"code": "MARKET_LANGUAGE_MISMATCH", "message": "locale retry worked"},
            {"code": "DESTINATION_MISMATCH", "message": "wrong country"},
        ]
        normalized = offer_io.normalize_export(payload)
        self.assertEqual(
            [item["code"] for item in normalized["errors"]],
            ["MARKET_LANGUAGE_MISMATCH", "DESTINATION_MISMATCH"],
        )

    def test_unknown_baggage_is_not_not_included(self):
        payload = export_with(
            [
                {
                    "kind": "flight",
                    "id": "flight-1",
                    "currency": "CNY",
                    "baggage_status": "unknown",
                    "costs": {"transport_fare": 500, "baggage": None},
                    "required_cost_fields": ["transport_fare", "baggage"],
                }
            ]
        )
        normalized = offer_io.normalize_export(payload)
        evidence = normalized["offers"][0]["evidence"]
        self.assertEqual(evidence["baggage_status"], "unknown")
        self.assertNotEqual(evidence["baggage_status"], "not_included")

    def test_web_search_is_allowed_only_as_explicit_evidence_type(self):
        payload = export_with(
            [
                {
                    "kind": "ferry",
                    "id": "ferry-discovery",
                    "currency": "CNY",
                    "evidence": {
                        "source_type": "web_search",
                        "price_status": "unavailable",
                        "completeness": "partial",
                    },
                    "costs": {"transport_fare": None},
                }
            ]
        )
        normalized = offer_io.normalize_export(payload)
        self.assertEqual(
            normalized["offers"][0]["evidence"]["source_type"], "web_search"
        )

    def test_non_finite_cost_is_rejected(self):
        normalized = offer_io.normalize_export(
            export_with(
                [
                    {
                        "kind": "flight",
                        "id": "flight-1",
                        "currency": "CNY",
                        "costs": {"transport_fare": math.inf},
                    },
                    {
                        "kind": "hotel",
                        "id": "hotel-1",
                        "currency": "CNY",
                        "costs": {"stay": 800},
                    },
                ]
            )
        )
        plans, warnings = offer_io.build_candidate_plans(
            normalized["offers"],
            target_currency="CNY",
        )
        self.assertEqual(plans, [])
        self.assertTrue(any("finite" in item for item in warnings))

    def test_missing_access_stays_unknown_in_evaluator(self):
        normalized = offer_io.normalize_export(
            export_with(
                [
                    {
                        "kind": "flight",
                        "id": "flight-1",
                        "currency": "CNY",
                        "costs": {"transport_fare": 500, "taxes": 100},
                        "required_cost_fields": ["transport_fare", "taxes"],
                    },
                    {
                        "kind": "hotel",
                        "id": "hotel-1",
                        "currency": "CNY",
                        "costs": {"stay": 800},
                        "required_cost_fields": ["stay"],
                    },
                ]
            )
        )
        plans, warnings = offer_io.build_candidate_plans(
            normalized["offers"],
            target_currency="CNY",
        )
        evaluated = travel_core.evaluate_plan(plans[0], {})
        self.assertFalse(evaluated["cost"]["complete"])
        self.assertIn("origin_access", evaluated["cost"]["missing_fields"])
        self.assertTrue(any("origin-access" in item for item in warnings))

    def test_zero_fx_rate_is_rejected(self):
        normalized = offer_io.normalize_export(
            export_with(
                [
                    {
                        "kind": "flight",
                        "id": "flight-1",
                        "currency": "USD",
                        "costs": {"transport_fare": 100},
                    },
                    {
                        "kind": "hotel",
                        "id": "hotel-1",
                        "currency": "CNY",
                        "costs": {"stay": 800},
                    },
                ]
            )
        )
        plans, warnings = offer_io.build_candidate_plans(
            normalized["offers"],
            target_currency="CNY",
            fx_rates={"USD/CNY": 0},
        )
        self.assertEqual(plans, [])
        self.assertTrue(any("must be positive" in item for item in warnings))


if __name__ == "__main__":
    unittest.main()
