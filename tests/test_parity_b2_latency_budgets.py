"""P-B2 runtime and watch summary latency budget tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.verify.check_latency_budget import run_check

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FIXTURE = REPO_ROOT / "scripts/verify/fixtures/runtime-summary-latency.ci.json"
WATCH_FIXTURE = REPO_ROOT / "scripts/verify/fixtures/watch-summary-latency.ci.json"


class ParityB2LatencyBudgetTests(unittest.TestCase):
    def test_runtime_summary_ci_fixture_passes_budget(self) -> None:
        result = run_check(
            "runtime_summary_latency",
            samples_file=RUNTIME_FIXTURE,
            strict_pending=True,
        )
        self.assertEqual("pass", result.status)

    def test_watch_summary_ci_fixture_passes_budget(self) -> None:
        result = run_check(
            "watch_summary_latency",
            samples_file=WATCH_FIXTURE,
            strict_pending=True,
        )
        self.assertEqual("pass", result.status)

    def test_default_verify_script_wires_latency_fixtures(self) -> None:
        package = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
        verify_script = package["scripts"]["verify"]
        self.assertIn("--runtime-latency-samples", verify_script)
        self.assertIn("--watch-latency-samples", verify_script)
        self.assertIn("runtime-summary-latency.ci.json", verify_script)
        self.assertIn("watch-summary-latency.ci.json", verify_script)


if __name__ == "__main__":
    unittest.main()
