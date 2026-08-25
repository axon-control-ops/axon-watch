"""VAXON fleet self-heal: config loading and defaults."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.fleet_self_heal.config import (  # noqa: E402
    clear_config_cache_for_tests,
    load_fleet_self_heal_config,
)


class FleetSelfHealConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_config_cache_for_tests()
        self.addCleanup(clear_config_cache_for_tests)

    def test_missing_file_falls_back_to_safe_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "does-not-exist.json"
            config = load_fleet_self_heal_config(path=missing)
        self.assertTrue(config.enabled)
        self.assertFalse(config.dispatch_enabled, "must default to dry-run, never auto-dispatch")
        self.assertEqual("workspace_axon_watch", config.target_workspace_id)
        self.assertEqual("watcher", config.owner_role)

    def test_loads_real_repo_config_file(self) -> None:
        config = load_fleet_self_heal_config(force_reload=True)
        self.assertTrue(config.enabled)
        self.assertEqual("workspace_axon_watch", config.target_workspace_id)
        self.assertEqual("watcher", config.owner_role)
        self.assertEqual("lead", config.escalate_role)
        self.assertEqual("backend", config.role_for_subsystem("persistence.run_store"))
        self.assertEqual("watcher", config.role_for_subsystem("some_unmapped_subsystem"))

    def test_thresholds_clamp_to_sane_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "target_workspace_id": "workspace_axon_watch",
                        "defaults": {"attempt_budget_per_dispatch": 999, "max_dispatch_cycles": 0},
                    }
                ),
                encoding="utf-8",
            )
            config = load_fleet_self_heal_config(path=path)
        self.assertEqual(32, config.attempt_budget_per_dispatch)
        self.assertEqual(1, config.max_dispatch_cycles)


if __name__ == "__main__":
    unittest.main()
