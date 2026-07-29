from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = (
    ROOT
    / "plugins"
    / "open-travel"
    / "skills"
    / "plan-open-travel"
    / "scripts"
    / "travel_core.py"
)
sys.path.insert(0, str(CORE_PATH.parent))
import travel_core  # noqa: E402


class TravelCoreTests(unittest.TestCase):
    def load_fixture(self):
        path = ROOT / "tests" / "fixtures" / "sample_plans.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_complete_cost_changes_headline_cheapest(self):
        result = travel_core.evaluate_payload(self.load_fixture())
        plans = {item["id"]: item for item in result["plans"]}
        self.assertEqual(plans["headline-cheap"]["cost"]["total"], 4880.0)
        self.assertEqual(plans["balanced"]["cost"]["total"], 4200.0)
        self.assertEqual(result["selected"]["lowest-cost"]["id"], "balanced")
        self.assertEqual(result["options"][0]["option_id"], "A")
        self.assertEqual(result["options"][0]["id"], "balanced")

    def test_late_red_eye_risks_are_flagged(self):
        result = travel_core.evaluate_payload(self.load_fixture())
        plans = {item["id"]: item for item in result["plans"]}
        codes = {risk["code"] for risk in plans["headline-cheap"]["risks"]}
        self.assertIn("red-eye", codes)
        self.assertIn("after-last-transit", codes)
        self.assertIn("after-checkin", codes)

    def test_missing_required_cost_is_not_zero(self):
        payload = self.load_fixture()
        payload["plans"] = [payload["plans"][1]]
        payload["plans"][0]["costs"]["taxes"] = None
        result = travel_core.evaluate_payload(payload)
        plan = result["plans"][0]
        self.assertIsNone(plan["cost"]["total"])
        self.assertIn("taxes", plan["cost"]["missing_fields"])
        self.assertEqual(result["selected"], {})
        self.assertEqual(result["options"], [])
        self.assertEqual(result["estimated_options"], [])

    def test_incomplete_plan_can_enter_separate_estimated_comparison(self):
        payload = self.load_fixture()
        payload["plans"] = [payload["plans"][1]]
        plan = payload["plans"][0]
        plan["costs"]["baggage"] = None
        plan["required_cost_fields"] = list(
            travel_core.DEFAULT_REQUIRED_COST_FIELDS
        ) + ["baggage"]
        plan["cost_estimates"] = {"baggage": {"min": 100, "max": 300}}
        result = travel_core.evaluate_payload(payload)
        self.assertEqual(result["options"], [])
        self.assertEqual(result["estimated_options"][0]["option_id"], "R1")
        self.assertEqual(
            result["estimated_options"][0]["estimated_range"],
            {"min": 4300.0, "max": 4500.0},
        )
        self.assertEqual(result["estimated_options"][0]["status"], "estimated-reference")

    def test_estimate_range_rejects_inverted_bounds(self):
        payload = self.load_fixture()
        payload["plans"] = [payload["plans"][1]]
        plan = payload["plans"][0]
        plan["costs"]["taxes"] = None
        plan["cost_estimates"] = {"taxes": {"min": 500, "max": 100}}
        with self.assertRaisesRegex(ValueError, "must not exceed"):
            travel_core.evaluate_payload(payload)

    def test_hard_constraint_filters_self_transfer(self):
        payload = self.load_fixture()
        payload["plans"] = [payload["plans"][1]]
        payload["plans"][0]["connection"]["self_transfer"] = True
        result = travel_core.evaluate_payload(payload)
        self.assertFalse(result["plans"][0]["eligible"])
        self.assertIn("不接受自助转机", result["plans"][0]["constraint_failures"])

    def test_duplicate_ids_are_rejected(self):
        payload = self.load_fixture()
        payload["plans"][1]["id"] = payload["plans"][0]["id"]
        with self.assertRaisesRegex(ValueError, "unique"):
            travel_core.evaluate_payload(payload)

    def test_non_finite_duration_is_rejected(self):
        payload = self.load_fixture()
        payload["plans"][0]["duration_minutes"] = math.inf
        with self.assertRaisesRegex(ValueError, "finite"):
            travel_core.evaluate_payload(payload)

    def test_options_are_stable_and_distinct(self):
        result = travel_core.evaluate_payload(self.load_fixture())
        options = result["options"]
        self.assertEqual(
            [item["option_id"] for item in options],
            [chr(ord("A") + index) for index in range(len(options))],
        )
        self.assertEqual(
            len({item["id"] for item in options}),
            len(options),
        )
        self.assertLessEqual(len(options), 5)
        balanced = next(item for item in options if item["id"] == "balanced")
        self.assertIn("lowest-cost", balanced["badges"])


if __name__ == "__main__":
    unittest.main()
