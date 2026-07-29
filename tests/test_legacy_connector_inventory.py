"""G4.1 legacy connector inventory contract tests."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(REPO_ROOT))

from scripts.verify.check_legacy_connector_inventory import (  # noqa: E402
    DEFAULT_SPEC_PATH,
    validate_legacy_connector_inventory,
)
from scripts.verify.common import load_json  # noqa: E402


class LegacyConnectorInventoryTests(unittest.TestCase):
    def test_default_inventory_contract_passes(self) -> None:
        result = validate_legacy_connector_inventory()
        self.assertEqual("pass", result.status, result.message)

    def test_watch_connector_ids_are_covered(self) -> None:
        spec = load_json(DEFAULT_SPEC_PATH)
        watch = load_json(REPO_ROOT / "config" / "watch-connectors.json")
        inventory_ids = {str(item["id"]) for item in spec["inventory"]}
        watch_ids = set(watch["connectors"].keys())
        self.assertTrue(watch_ids.issubset(inventory_ids))

    def test_unmigrated_entries_name_phase_g_owner_and_probe(self) -> None:
        spec = load_json(DEFAULT_SPEC_PATH)
        for entry in spec["inventory"]:
            status = str(entry["axon_x_status"])
            if status not in {"unmigrated", "partial", "optional_fallback"}:
                continue
            self.assertTrue(str(entry["owner"]).strip(), entry["id"])
            self.assertTrue(str(entry["phase_g_slice"]).strip(), entry["id"])
            self.assertTrue(str(entry["probe"]).strip() or isinstance(entry["probe"], dict), entry["id"])
            self.assertGreaterEqual(len(str(entry["removal_criteria"])), 24, entry["id"])

    def test_retirement_blocker_map_matches_parity_snapshot(self) -> None:
        spec = load_json(DEFAULT_SPEC_PATH)
        snapshot = load_json(REPO_ROOT / "config" / "parity-snapshot.json")
        blocker_text = snapshot["blockers_for_full_retirement"][0]
        self.assertIn(blocker_text, spec["retirement_blocker_map"])

    def test_rejects_missing_watch_connector_mapping(self) -> None:
        spec = copy.deepcopy(load_json(DEFAULT_SPEC_PATH))
        spec["inventory"] = [
            item for item in spec["inventory"] if item["id"] != "control_plane"
        ]
        result = validate_legacy_connector_inventory(spec=spec)
        self.assertEqual("fail", result.status)
        self.assertIn("control_plane", result.message)


if __name__ == "__main__":
    unittest.main()
