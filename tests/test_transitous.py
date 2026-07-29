from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


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
import transitous  # noqa: E402


class TransitousTests(unittest.TestCase):
    def test_normalizes_itinerary_and_preserves_attribution(self):
        calls = []

        def fake_fetch(url, params, timeout, user_agent):
            calls.append((url, params, timeout, user_agent))
            return {
                "itineraries": [
                    {
                        "duration": 1800,
                        "transfers": 1,
                        "startTime": "2026-09-15T09:00:00+09:00",
                        "endTime": "2026-09-15T09:30:00+09:00",
                        "legs": [
                            {
                                "mode": "WALK",
                                "duration": 300,
                                "distance": 420,
                                "from": {"name": "Hotel"},
                                "to": {"name": "Station"},
                            },
                            {
                                "mode": "SUBWAY",
                                "duration": 1500,
                                "from": {"name": "Station"},
                                "to": {"name": "Airport"},
                                "agency": {"name": "Metro"},
                                "route": {"shortName": "A"},
                                "realTime": False,
                            },
                        ],
                    }
                ]
            }

        result = transitous.plan_routes(
            [35.68, 139.76],
            [35.55, 139.78],
            "2026-09-15T09:00:00+09:00",
            contact="me@example.test",
            fetch_json=fake_fetch,
        )
        offer = result["offers"][0]
        self.assertEqual(offer["duration_minutes"], 30)
        self.assertEqual(offer["walking_meters"], 420)
        self.assertEqual(offer["fare"], None)
        self.assertEqual(
            offer["evidence"]["attribution_url"], transitous.ATTRIBUTION_URL
        )
        self.assertIn("me@example.test", calls[0][3])
        self.assertEqual(calls[0][1]["detailedTransfers"], "true")

    def test_contact_is_required(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "requires contact"):
                transitous.plan_routes(
                    [35.68, 139.76],
                    [35.55, 139.78],
                    "2026-09-15T09:00:00+09:00",
                    fetch_json=lambda *_: {},
                )

    def test_rejects_naive_datetime(self):
        with self.assertRaisesRegex(ValueError, "timezone"):
            transitous.plan_routes(
                [35.68, 139.76],
                [35.55, 139.78],
                "2026-09-15T09:00:00",
                contact="me@example.test",
                fetch_json=lambda *_: {},
            )


if __name__ == "__main__":
    unittest.main()
