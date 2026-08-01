"""Gate 6 skips console-web typecheck/build when those paths are untouched."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.verifier_runner import (  # noqa: E402
    code_paths_touched,
    console_web_paths_touched,
    execute_check_plan,
    filter_runtime_noise_paths,
    is_runtime_noise_path,
)


class Gate6PathScopedChecksTests(unittest.TestCase):
    def test_console_web_touch_detection(self) -> None:
        self.assertFalse(console_web_paths_touched([]))
        self.assertFalse(
            console_web_paths_touched(
                [
                    "services/control-plane/app/workspace_agents/failure_detail.py",
                    "docs/ops/agent-reports/note.md",
                ]
            )
        )
        self.assertTrue(
            console_web_paths_touched(["apps/console-web/src/App.vue"])
        )

    def test_runtime_noise_filter_drops_cursor_mcp(self) -> None:
        self.assertTrue(is_runtime_noise_path(".cursor/mcp.json"))
        self.assertTrue(is_runtime_noise_path("./.cursor/mcp.json"))
        self.assertTrue(is_runtime_noise_path(".axon-si/baseline.json"))
        self.assertFalse(is_runtime_noise_path("docs/ops/agent-reports/note.md"))
        # str.lstrip('./') would wrongly turn ".cursor/..." into "cursor/..."
        self.assertFalse(is_runtime_noise_path("cursor/mcp.json"))
        self.assertEqual(
            filter_runtime_noise_paths(
                [".cursor/mcp.json", "docs/ops/agent-reports/note.md"]
            ),
            ["docs/ops/agent-reports/note.md"],
        )

    def test_code_paths_touched_ignores_docs_and_cursor(self) -> None:
        self.assertFalse(code_paths_touched([]))
        self.assertFalse(
            code_paths_touched([".cursor/mcp.json", "docs/ops/agent-reports/a.md"])
        )
        self.assertTrue(
            code_paths_touched(
                ["services/control-plane/app/workspace_agents/verifier_runner.py"]
            )
        )

    def test_execute_check_plan_skips_frontend_heavy_when_untouched(self) -> None:
        contract = {
            "commands": {
                "lint": ["true"],
                "typecheck": ["npm run typecheck --workspace=apps/console-web"],
                "test": ["true"],
                "build": ["npm run build --workspace=apps/console-web"],
                "security": ["true"],
                "diff_budget": ["true"],
            },
            "verifier": {
                "required_checks": [
                    "lint",
                    "typecheck",
                    "test",
                    "build",
                    "security",
                    "diff_budget",
                ]
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("subprocess.run") as run_mock:
                run_mock.return_value = mock.Mock(
                    returncode=0, stdout="ok", stderr=""
                )
                results = execute_check_plan(
                    Path(tmp),
                    contract,
                    changed_paths=[
                        "services/control-plane/app/workspace_agents/failure_detail.py"
                    ],
                )
        self.assertTrue(results["typecheck"]["passed"])
        self.assertIn("skipped", results["typecheck"]["output_excerpt"])
        self.assertTrue(results["build"]["passed"])
        self.assertIn("skipped", results["build"]["output_excerpt"])
        # lint/test/security/diff_budget still invoked
        self.assertEqual(run_mock.call_count, 4)

    def test_execute_check_plan_skips_code_heavy_for_cursor_only_dirty(self) -> None:
        contract = {
            "commands": {
                "lint": ["false"],
                "typecheck": ["false"],
                "test": ["false"],
                "build": ["false"],
                "security": ["false"],
                "diff_budget": ["false"],
            },
            "verifier": {
                "required_checks": [
                    "lint",
                    "typecheck",
                    "test",
                    "build",
                    "security",
                    "diff_budget",
                ]
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("subprocess.run") as run_mock:
                results = execute_check_plan(
                    Path(tmp),
                    contract,
                    changed_paths=[".cursor/mcp.json"],
                )
        self.assertEqual(run_mock.call_count, 0)
        for name in ("lint", "typecheck", "test", "build", "security", "diff_budget"):
            self.assertTrue(results[name]["passed"], name)
            self.assertIn("skipped", results[name]["output_excerpt"])

    def test_execute_check_plan_runs_frontend_when_console_web_dirty(self) -> None:
        contract = {
            "commands": {
                "typecheck": ["echo typecheck"],
                "build": ["echo build"],
            },
            "verifier": {"required_checks": ["typecheck", "build"]},
        }
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("subprocess.run") as run_mock:
                run_mock.return_value = mock.Mock(
                    returncode=0, stdout="ok", stderr=""
                )
                results = execute_check_plan(
                    Path(tmp),
                    contract,
                    changed_paths=["apps/console-web/src/App.vue"],
                )
        self.assertEqual(run_mock.call_count, 2)
        self.assertTrue(results["typecheck"]["passed"])
        self.assertNotIn("skipped", results["typecheck"]["output_excerpt"])


if __name__ == "__main__":
    unittest.main()
