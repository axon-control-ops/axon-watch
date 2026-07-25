from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.readiness import (  # noqa: E402
    cli_runtime_degraded_reasons,
    summarize_cli_runtime_readiness,
)


class CliRuntimeReadinessTests(unittest.TestCase):
    def test_summarize_marks_dispatch_ready_when_any_local_runtime_ready(self) -> None:
        snapshot = {
            "default_runtime": "codex_local",
            "local": [
                {
                    "id": "cursor_local",
                    "label": "Cursor CLI (local)",
                    "ready": False,
                    "available": True,
                    "auth": {"message": "Cursor auth probe timed out."},
                },
                {
                    "id": "codex_local",
                    "label": "Codex CLI (local)",
                    "ready": True,
                    "available": True,
                    "auth": {"message": "Authenticated via Codex/OpenAI API key from vault."},
                },
            ],
        }
        summary = summarize_cli_runtime_readiness(snapshot)
        self.assertTrue(summary["dispatch_ready"])
        self.assertEqual(1, summary["ready_count"])
        self.assertTrue(summary["default_ready"])
        self.assertEqual(1, len(summary["blockers"]))

    def test_degraded_reasons_when_no_local_runtime_ready(self) -> None:
        snapshot = {
            "default_runtime": "cursor_local",
            "local": [
                {
                    "id": "cursor_local",
                    "label": "Cursor CLI (local)",
                    "ready": False,
                    "available": True,
                    "auth": {"message": "Cursor auth probe timed out."},
                },
                {
                    "id": "codex_local",
                    "label": "Codex CLI (local)",
                    "ready": False,
                    "available": True,
                    "auth": {"message": "Codex/OpenAI API key was rejected."},
                },
            ],
        }
        reasons = cli_runtime_degraded_reasons(snapshot)
        self.assertEqual(1, len(reasons))
        self.assertIn("CLI runtime not ready", reasons[0])
        self.assertIn("Cursor auth probe timed out", reasons[0])


if __name__ == "__main__":
    unittest.main()
