"""P-D6 dock behavior and browser startup parity tests."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class ParityD6DockAndStartupTests(unittest.TestCase):
    def test_default_verify_wiring_includes_parity_d6_tests(self) -> None:
        from tests.verify_contract_wiring import contract_verify_wiring_surface

        verify_script = contract_verify_wiring_surface()
        self.assertIn("tests.test_parity_d6_dock_and_startup", verify_script)

    def test_snapshot_rows_promoted_to_verified(self) -> None:
        snapshot = json.loads((REPO_ROOT / "config" / "parity-snapshot.json").read_text(encoding="utf-8"))
        for parity_id in ("dock_behavior", "desktop_and_browser_startup"):
            row = next(entry for entry in snapshot["behaviors"] if entry["id"] == parity_id)
            with self.subTest(parity_id=parity_id):
                self.assertEqual("verified", row["status"])
        summary = snapshot["summary"]
        self.assertEqual(0, summary["partially_verified"])
        self.assertEqual(19, summary["verified_v1"])

    def test_dock_and_browser_contract_checkers_pass(self) -> None:
        for script in (
            "scripts/verify/check_dock_behavior_contract.py",
            "scripts/verify/check_browser_startup_contract.py",
        ):
            result = subprocess.run(
                [sys.executable, script],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
