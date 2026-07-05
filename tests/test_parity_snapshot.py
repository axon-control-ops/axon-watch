"""Final parity snapshot verification."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_FILE = REPO_ROOT / "config" / "parity-snapshot.json"
DECISION_FILE = REPO_ROOT / "docs" / "CUTOVER_DECISION.md"


class ParitySnapshotTests(unittest.TestCase):
    def test_snapshot_file_exists(self) -> None:
        self.assertTrue(SNAPSHOT_FILE.is_file())

    def test_check_parity_snapshot_script_passes(self) -> None:
        result = subprocess.run(
            ["python3", "scripts/verify/check_parity_snapshot.py"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)

    def test_bounded_cutover_not_full_retirement(self) -> None:
        payload = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
        self.assertEqual("bounded_cutover_approved", payload["decision"])
        self.assertFalse(payload["full_axon_local_retirement"])
        self.assertEqual(0, payload["summary"]["partially_verified"])
        self.assertEqual(19, payload["summary"]["verified_v1"])
        self.assertGreaterEqual(len(payload["blockers_for_full_retirement"]), 1)

    def test_all_test_gates_listed_through_test9(self) -> None:
        payload = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
        gates = payload["required_gates_passed"]
        for index in range(10):
            self.assertIn(f"TEST-{index}", gates)

    def test_decision_doc_declares_not_approved_retirement(self) -> None:
        text = DECISION_FILE.read_text(encoding="utf-8")
        self.assertIn("NOT APPROVED", text)
        self.assertIn("Bounded Axon-X cutover", text)


if __name__ == "__main__":
    unittest.main()
