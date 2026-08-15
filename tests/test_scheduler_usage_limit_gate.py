"""Usage-limit auto-start gate must route to the runtime that actually failed.

Regression coverage for a bug where a Claude Code usage-limit failure always
consulted Cursor's usage pool (the only probe the gate ever called), so a
Claude-only workspace could never correctly back off — and could falsely
soft-open on leftover Cursor headroom unrelated to the real block.
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from tests.support.control_plane_app_loader import prepare_control_plane_imports

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


class UsageLimitGateRuntimeRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        prepare_control_plane_imports()
        from app.cli_runtime.claude_usage_probe import reset_claude_usage_limit_state_for_tests

        self.reset_claude_usage_limit_state_for_tests = reset_claude_usage_limit_state_for_tests
        reset_claude_usage_limit_state_for_tests()
        self.addCleanup(reset_claude_usage_limit_state_for_tests)

    def test_claude_usage_limit_blocks_even_when_cursor_has_headroom(self) -> None:
        from app.workspace_agents.scheduler_auto_start_gates import usage_limit_blocks_auto_start

        future_epoch = int(time.time()) + 3600
        detail = f"Claude AI usage limit reached|{future_epoch}"
        with patch(
            "app.workspace_agents.scheduler_auto_start_gates.latest_role_run_outcome",
            return_value={"outcome": "failed", "detail": detail},
        ), patch(
            "app.cli_runtime.cursor_usage_probe.probe_cursor_usage",
            return_value={"ok": True, "auto_percent_used": 5, "total_percent_used": 5},
        ), patch(
            "app.cli_runtime.claude_usage_probe.probe_claude_usage",
            return_value={"ok": True, "limit_reached": True},
        ), patch(
            "app.cli_runtime.claude_usage_probe.claude_usage_allows_agent_retry",
            return_value=False,
        ):
            blocked = usage_limit_blocks_auto_start("workspace_axon_watch", "backend")
        self.assertTrue(
            blocked,
            "Claude usage-limit failure must not soft-open off Cursor's unrelated headroom",
        )

    def test_claude_usage_limit_soft_opens_after_reset(self) -> None:
        from app.workspace_agents.scheduler_auto_start_gates import usage_limit_blocks_auto_start

        past_epoch = int(time.time()) - 10
        detail = f"Claude AI usage limit reached|{past_epoch}"
        with patch(
            "app.workspace_agents.scheduler_auto_start_gates.latest_role_run_outcome",
            return_value={"outcome": "failed", "detail": detail},
        ):
            blocked = usage_limit_blocks_auto_start("workspace_axon_watch", "backend")
        self.assertFalse(blocked)

    def test_cursor_usage_limit_still_routes_to_cursor_probe(self) -> None:
        from app.workspace_agents.scheduler_auto_start_gates import usage_limit_blocks_auto_start

        with patch(
            "app.workspace_agents.scheduler_auto_start_gates.latest_role_run_outcome",
            return_value={
                "outcome": "failed",
                "detail": "You've hit your usage limit for Cursor Auto.",
            },
        ), patch(
            "app.cli_runtime.cursor_usage_probe.probe_cursor_usage",
            return_value={"ok": True, "auto_percent_used": 10, "total_percent_used": 10},
        ):
            blocked = usage_limit_blocks_auto_start("workspace_axon_watch", "backend")
        self.assertFalse(blocked)


if __name__ == "__main__":
    unittest.main()
