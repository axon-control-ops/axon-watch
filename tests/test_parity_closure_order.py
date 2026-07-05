"""Parity closure order verification."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class ParityClosureOrderTests(unittest.TestCase):
    def test_check_parity_closure_passes(self) -> None:
        result = subprocess.run(
            ["python3", "scripts/verify/check_parity_closure.py"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)

    def test_p_a1_marked_done_in_closure_order(self) -> None:
        order = json.loads(
            (REPO_ROOT / "config" / "parity-closure-order.json").read_text(encoding="utf-8")
        )
        p_a1 = next(entry for entry in order["slices"] if entry["id"] == "P-A1")
        self.assertEqual("done", p_a1["status"])
        self.assertEqual("P-A2", order["next_slice"])

    def test_run_stop_resume_promoted_in_snapshot(self) -> None:
        snapshot = json.loads(
            (REPO_ROOT / "config" / "parity-snapshot.json").read_text(encoding="utf-8")
        )
        row = next(entry for entry in snapshot["behaviors"] if entry["id"] == "run_stop_resume")
        self.assertEqual("verified", row["status"])
        self.assertEqual(8, snapshot["summary"]["verified_v1"])


if __name__ == "__main__":
    unittest.main()
