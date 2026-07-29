from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "open-travel"
SKILL = PLUGIN / "skills" / "plan-open-travel"


class PackageContractTests(unittest.TestCase):
    def test_manifest_declares_skill_and_remote_mcps(self):
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "open-travel")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")
        servers = json.loads(
            (PLUGIN / ".mcp.json").read_text(encoding="utf-8")
        )["mcpServers"]
        self.assertEqual(
            set(servers), {"travel_12306", "travel_kiwi", "travel_hotels"}
        )
        self.assertEqual(servers["travel_12306"]["command"], "npx")
        self.assertEqual(
            servers["travel_12306"]["args"], ["-y", "12306-mcp@0.3.9"]
        )
        self.assertNotIn("cwd", servers["travel_12306"])
        self.assertEqual(
            servers["travel_kiwi"],
            {"type": "http", "url": "https://mcp.kiwi.com"},
        )
        self.assertEqual(
            servers["travel_hotels"],
            {"type": "http", "url": "https://mcp.trivago.com/mcp"},
        )

    def test_active_local_scripts_have_explicit_roles(self):
        scripts = {path.name for path in (SKILL / "scripts").glob("*.py")}
        self.assertEqual(
            scripts,
            {
                "evaluate_plans.py",
                "offer_io.py",
                "public_data.py",
                "transitous.py",
                "travel_core.py",
            },
        )

    def test_routing_names_installed_plugin_capabilities(self):
        routing = (SKILL / "references" / "tool-routing.md").read_text(
            encoding="utf-8"
        )
        for provider in (
            "Skyscanner",
            "Trip.com",
            "Kiwi",
            "12306",
            "trivago",
            "Klook",
            "Wikiloc",
        ):
            self.assertIn(provider, routing)
        self.assertNotIn("Skiplagged", routing)
        self.assertNotIn("Airbnb", routing)

    def test_repository_has_no_machine_local_mcp_runtime(self):
        self.assertFalse((ROOT / ".codex" / "config.toml").exists())
        self.assertFalse((ROOT / "mcp").exists())
        self.assertFalse((ROOT / ".pnpm-store").exists())
        self.assertFalse((PLUGIN / ".runtime").exists())
        self.assertFalse((ROOT / ".agents" / "skills").exists())

    def test_repo_marketplace_points_to_canonical_plugin(self):
        marketplace = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(marketplace["name"], "open-travel")
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], "open-travel")
        self.assertEqual(
            entry["source"],
            {"source": "local", "path": "./plugins/open-travel"},
        )
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")

    def test_open_source_metadata_is_present(self):
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["license"], "MIT")
        self.assertTrue((ROOT / "LICENSE").exists())
        self.assertTrue((ROOT / "README.md").exists())

    def test_skill_requires_local_capability_classification(self):
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        policy = (SKILL / "references" / "local-capabilities.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("local-capabilities.md", skill)
        self.assertIn("## Core:", policy)
        self.assertIn("## Conditional:", policy)
        self.assertIn("## Retired:", policy)

    def test_output_contract_provides_standardized_choices(self):
        output = (SKILL / "references" / "output-schema.md").read_text(
            encoding="utf-8"
        )
        for requirement in (
            "three to five",
            "`A` through `E`",
            "`recommended`",
            "`lowest-cost`",
            "`fastest`",
            "`low-hassle`",
            "`comfort`",
            "Choice prompt",
        ):
            self.assertIn(requirement, output)

    def test_provider_feedback_guardrails_are_linked(self):
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        quirks = (SKILL / "references" / "provider-quirks.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("provider-quirks.md", skill)
        for requirement in (
            "DD/MM/YYYY",
            "SUPPLIER_UNSUPPORTED",
            "not_returned",
            "PASSENGER_COUNT_MISMATCH",
        ):
            self.assertIn(requirement, quirks)

    def test_surface_transport_uses_global_layered_sources(self):
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        surface = (SKILL / "references" / "surface-transport.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("surface-transport.md", skill)
        for requirement in (
            "Transitous",
            "search the internet automatically",
            "official operator",
            "web_search",
            "NO_INVENTORY",
            "NOT_ON_SALE",
        ):
            self.assertIn(requirement, surface)
        for regional_patch in (
            "Malaysia",
            "Southeast Asia",
            "Penang",
            "Langkawi",
            "Kuala Perlis",
            "Kuala Kedah",
        ):
            self.assertNotIn(regional_patch, surface)

    def test_trivago_contract_handles_market_and_destination_mismatch(self):
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        contract = (SKILL / "references" / "trivago.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("trivago.md", skill)
        for requirement in (
            "rooms <= adults",
            "shopper pricing/content market",
            "does not include `CN`",
            "`MARKET_LANGUAGE_MISMATCH`",
            "`DESTINATION_MISMATCH`",
            "trivago_accommodation_radius_search",
            "structuredContent.accommodations",
            "price_per_stay",
        ):
            self.assertIn(requirement, contract)

    def test_provider_availability_distinguishes_public_and_store_only_sources(self):
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        availability = (
            SKILL / "references" / "provider-availability.md"
        ).read_text(encoding="utf-8")
        self.assertIn("provider-availability.md", skill)
        for public_endpoint in (
            "https://mcp.kiwi.com",
            "https://mcp.trivago.com/mcp",
        ):
            self.assertIn(public_endpoint, availability)
        for restricted_or_store_only in (
            "Skyscanner",
            "Trip.com",
            "Klook",
            "Wikiloc",
        ):
            self.assertIn(restricted_or_store_only, availability)
        self.assertIn("case by case", availability)
        self.assertIn("No provider-published public MCP endpoint found", availability)
        self.assertIn("official web sources", availability)

    def test_estimated_comparison_stays_separate_from_primary_options(self):
        ranking = (SKILL / "references" / "ranking-rules.md").read_text(
            encoding="utf-8"
        )
        output = (SKILL / "references" / "output-schema.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("estimated_options", ranking)
        self.assertIn("R1", output)
        self.assertIn("Never mix", output)


if __name__ == "__main__":
    unittest.main()
