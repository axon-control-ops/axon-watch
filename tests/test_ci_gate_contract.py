from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CiGateContractTests(unittest.TestCase):
    def test_fast_gate_is_strict_and_runs_autonomy_suites(self) -> None:
        workflow = (ROOT / ".github/workflows/fast-gate.yml").read_text(encoding="utf-8")
        contract_runner = (ROOT / "scripts/verify/run_contract_unit_tests.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("npm run verify:contracts", workflow)
        self.assertIn("npm run verify:console-web", workflow)
        self.assertIn("--strict-pending", workflow)
        self.assertIn("tests.test_kairo_conversation_endpoints", contract_runner)
        self.assertIn("tests.test_conversation_transcript", contract_runner)

    def test_nightly_requires_live_evidence_and_uploads_receipts(self) -> None:
        workflow = (ROOT / ".github/workflows/nightly-verify.yml").read_text(encoding="utf-8")

        self.assertIn("./scripts/dev/up.sh", workflow)
        self.assertIn("./scripts/dev/collect-verify-evidence.sh", workflow)
        self.assertIn("--require-live-evidence", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("./scripts/dev/down.sh", workflow)

    def test_local_commit_preflight_is_blocking(self) -> None:
        script = (ROOT / "scripts/sc").read_text(encoding="utf-8")

        self.assertIn("npm --prefix \"$REPO_ROOT\" run verify:preflight", script)
        self.assertIn('die "verification preflight failed; commit aborted"', script)
        self.assertNotIn("commit will still proceed", script)
        self.assertNotIn("--quick", script)


if __name__ == "__main__":
    unittest.main()
