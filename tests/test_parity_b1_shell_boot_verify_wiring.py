"""P-B1 initial shell boot verify wiring tests."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from scripts.verify.check_latency_budget import run_check

REPO_ROOT = Path(__file__).resolve().parents[1]
SHELL_BOOT_FIXTURE = REPO_ROOT / "scripts/verify/fixtures/shell-boot-report.dev.json"


class ParityB1ShellBootVerifyWiringTests(unittest.TestCase):
    def test_shell_boot_fixture_passes_readiness_gate(self) -> None:
        result = run_check(
            "shell_boot_readiness",
            samples_file=SHELL_BOOT_FIXTURE,
            strict_pending=True,
        )
        self.assertEqual("pass", result.status)

    def test_default_verify_script_wires_shell_boot_report(self) -> None:
        package = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
        verify_script = package["scripts"]["verify"]
        self.assertIn("--shell-boot-report", verify_script)
        self.assertIn("shell-boot-report.dev.json", verify_script)

    def test_all_py_passes_shell_boot_with_default_fixtures(self) -> None:
        result = subprocess.run(
            [
                "python3",
                "scripts/verify/all.py",
                "--runtime-payload",
                "packages/shared-types/fixtures/runtime-summary.example.json",
                "--watch-payload",
                "packages/shared-types/fixtures/watch-summary.example.json",
                "--shell-boot-report",
                str(SHELL_BOOT_FIXTURE.relative_to(REPO_ROOT)),
                "--runtime-latency-samples",
                "scripts/verify/fixtures/runtime-summary-latency.ci.json",
                "--watch-latency-samples",
                "scripts/verify/fixtures/watch-summary-latency.ci.json",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)
        self.assertIn("shell_boot_readiness", result.stdout)
        self.assertIn("pass", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
