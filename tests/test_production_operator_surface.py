"""Production operator surface declaration tests."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class ProductionOperatorSurfaceTests(unittest.TestCase):
    def test_operator_production_config_present(self) -> None:
        spec_path = REPO_ROOT / "config" / "operator-production.json"
        self.assertTrue(spec_path.is_file())
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        self.assertEqual("axon_x", spec["status"])
        self.assertIn(":4173", spec["primary_url"])

    def test_snapshot_declares_axon_x_production(self) -> None:
        snapshot = json.loads(
            (REPO_ROOT / "config" / "parity-snapshot.json").read_text(encoding="utf-8")
        )
        production = snapshot.get("production_operator")
        self.assertIsInstance(production, dict)
        assert isinstance(production, dict)
        self.assertEqual("axon_x", production.get("status"))
        self.assertIn(":4173", str(production.get("primary_url", "")))
        blockers = snapshot.get("blockers_for_full_retirement", [])
        self.assertFalse(
            any("7734 remains production operator reference" in item for item in blockers),
            msg="operator sign-off blocker should be cleared",
        )

    def test_production_operator_checker_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/verify/check_production_operator_surface.py"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
