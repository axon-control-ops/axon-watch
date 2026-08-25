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

    def test_axon_local_runtime_retired(self) -> None:
        payload = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
        self.assertEqual("axon_local_runtime_retired", payload["decision"])
        self.assertTrue(payload["full_axon_local_retirement"])
        self.assertEqual(0, payload["summary"]["partially_verified"])
        self.assertEqual(19, payload["summary"]["verified_v1"])
        self.assertEqual([], payload["blockers_for_full_retirement"])
        production = payload.get("production_operator")
        self.assertIsInstance(production, dict)
        assert isinstance(production, dict)
        self.assertEqual("axon_x", production.get("status"))
        self.assertIn(":4173", str(production.get("primary_url", "")))
        self.assertIsNone(production.get("fallback_url"))

    def test_all_test_gates_listed_through_test9(self) -> None:
        payload = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
        gates = payload["required_gates_passed"]
        for index in range(10):
            self.assertIn(f"TEST-{index}", gates)

    def test_decision_doc_declares_retirement(self) -> None:
        text = DECISION_FILE.read_text(encoding="utf-8")
        self.assertIn("APPROVED", text)
        self.assertIn("Bounded Axon-X cutover", text)
        self.assertIn("axon-local runtime retirement", text)


if __name__ == "__main__":
    unittest.main()
