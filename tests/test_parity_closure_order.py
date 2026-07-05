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

    def test_phase_a_complete_and_next_slice_is_p_b1(self) -> None:
        order = json.loads(
            (REPO_ROOT / "config" / "parity-closure-order.json").read_text(encoding="utf-8")
        )
        phase_a = [entry for entry in order["slices"] if entry.get("phase") == "A"]
        self.assertEqual(4, len(phase_a))
        self.assertTrue(all(entry["status"] == "done" for entry in phase_a))
        self.assertEqual("P-B1", order["next_slice"])

    def test_phase_a_parity_rows_verified_in_snapshot(self) -> None:
        snapshot = json.loads(
            (REPO_ROOT / "config" / "parity-snapshot.json").read_text(encoding="utf-8")
        )
        for parity_id in (
            "run_stop_resume",
            "approval_boundaries",
            "review_ready_state",
            "signal_inbox_consistency",
        ):
            row = next(entry for entry in snapshot["behaviors"] if entry["id"] == parity_id)
            with self.subTest(parity_id=parity_id):
                self.assertEqual("verified", row["status"])
        self.assertEqual(11, snapshot["summary"]["verified_v1"])
        self.assertEqual(8, snapshot["summary"]["partially_verified"])


if __name__ == "__main__":
    unittest.main()
