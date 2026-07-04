from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "dev"))

from measure_shell_boot import measure_bootstrap_critical_path, measure_shell_boot  # noqa: E402


class MeasureShellBootTests(unittest.TestCase):
    def test_bootstrap_critical_path_report_shape(self) -> None:
        with patch(
            "measure_shell_boot._fetch",
            side_effect=lambda url, timeout_seconds: None,
        ), patch("measure_shell_boot.urllib.request.urlopen") as urlopen_mock:
            response_mock = urlopen_mock.return_value.__enter__.return_value
            response_mock.read.return_value = b"<html></html>"

            payload = measure_bootstrap_critical_path(
                console_base_url="http://127.0.0.1:4173",
                control_plane_base_url="http://127.0.0.1:8787",
                timeout_seconds=2.0,
            )

        self.assertEqual("bootstrap-critical-path", payload["source"])
        self.assertIn("shell_ready_ms", payload)
        self.assertGreater(float(payload["shell_ready_ms"]), 0)
        self.assertEqual(
            [
                "/api/runtime/summary",
                "/api/inbox",
                "/api/briefing",
                "/api/workspaces",
                "/api/runs",
            ],
            payload["bootstrap_routes"],
        )

    def test_auto_mode_falls_back_without_playwright(self) -> None:
        with patch(
            "measure_shell_boot.measure_bootstrap_critical_path",
            return_value={"shell_ready_ms": 512.0, "source": "bootstrap-critical-path"},
        ) as bootstrap_mock:
            payload = measure_shell_boot(
                console_base_url="http://127.0.0.1:4173",
                control_plane_base_url="http://127.0.0.1:8787",
                mode="auto",
                timeout_seconds=2.0,
            )

        bootstrap_mock.assert_called_once()
        self.assertEqual(512.0, payload["shell_ready_ms"])

    def test_example_shell_boot_report_passes_verify_gate(self) -> None:
        from scripts.verify.check_latency_budget import run_check

        fixture = REPO_ROOT / "scripts/verify/fixtures/shell-boot-report.dev.json"
        result = run_check(
            "shell_boot_readiness",
            samples_file=fixture,
            strict_pending=True,
        )
        self.assertEqual("pass", result.status)
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertLessEqual(float(payload["shell_ready_ms"]), 2500)


if __name__ == "__main__":
    unittest.main()
