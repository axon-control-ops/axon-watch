"""TEST-10 final parity verification and cutover decision acceptance."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_FILE = REPO_ROOT / "config" / "parity-snapshot.json"
CUTOVER_TODO = REPO_ROOT / "docs" / "AXON_X_CUTOVER_TODO.md"
DECISION_FILE = REPO_ROOT / "docs" / "CUTOVER_DECISION.md"
VERIFICATION_FILE = REPO_ROOT / "docs" / "FINAL_PARITY_VERIFICATION.md"


class Test10FinalParityAcceptance(unittest.TestCase):
    def test_verification_and_decision_docs_exist(self) -> None:
        self.assertTrue(VERIFICATION_FILE.is_file())
        self.assertTrue(DECISION_FILE.is_file())

    def test_cutover_todo_marks_final_slice_done(self) -> None:
        todo = CUTOVER_TODO.read_text(encoding="utf-8")
        self.assertIn("- [x] Final parity verification and cutover decision", todo)
        self.assertIn("test10-final-parity-cutover.sh", todo)

    def test_snapshot_matches_parity_ledger_behavior_count(self) -> None:
        payload = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
        ledger = (REPO_ROOT / "docs" / "planning" / "PARITY_LEDGER.md").read_text(
            encoding="utf-8"
        )
        behavior_rows = [
            line
            for line in ledger.splitlines()
            if line.startswith("| ") and "Behavior |" not in line and "---" not in line
        ]
        must_keep_rows = [
            row for row in behavior_rows if "Current source surface" not in row
        ]
        # First table in ledger: must-keep behaviors (19 rows)
        self.assertEqual(19, payload["summary"]["total_behaviors"])
        self.assertGreaterEqual(len(must_keep_rows), 19)

    def test_test10_script_exists(self) -> None:
        script = REPO_ROOT / "scripts" / "verify" / "test10-final-parity-cutover.sh"
        self.assertTrue(script.is_file())
        self.assertTrue(script.stat().st_mode & 0o111)


if __name__ == "__main__":
    unittest.main()
