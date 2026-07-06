"""Tests for runtime fabric approval gate (Phase G G3.3)."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.approval_gate import (  # noqa: E402
    agent_tool_execution_enabled,
    lane_b_agent_requires_approval,
    resolve_runtime_execution_tier,
    runtime_dispatch_blocked_reason,
)
from app.cli_runtime.cursor_agent import run_cursor_local  # noqa: E402


class ApprovalGateTests(unittest.TestCase):
    def test_agent_stays_consultative_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AXON_WATCH_AGENT_TOOL_EXECUTION", None)
            self.assertFalse(agent_tool_execution_enabled())
            self.assertFalse(lane_b_agent_requires_approval())
            self.assertEqual(
                "consultative",
                resolve_runtime_execution_tier(composer_mode="agent", run_phase="executing"),
            )

    def test_full_access_consent_replaces_per_run_approval(self) -> None:
        self.assertTrue(agent_tool_execution_enabled("full"))
        # Consent in the Agent Dock is the approval; no run-level boundary.
        self.assertFalse(lane_b_agent_requires_approval("full"))
        self.assertEqual(
            "executing",
            resolve_runtime_execution_tier(
                composer_mode="agent",
                run_phase="executing",
                execution_access="full",
            ),
        )
        reason = runtime_dispatch_blocked_reason(
            composer_mode="agent",
            run_phase="awaiting_approval",
            execution_access="full",
        )
        self.assertIsNotNone(reason)
        self.assertIn("approval", reason.lower())

    _STREAM_OK = (
        '{"type":"assistant","message":{"role":"assistant","content":'
        '[{"type":"text","text":"ok"}]}}\n'
        '{"type":"result","subtype":"success","is_error":false,"result":"ok"}\n'
    )

    @patch("app.cli_runtime.cursor_agent.communicate_registered_process")
    def test_cursor_agent_uses_plan_until_executing_tier(self, mock_communicate) -> None:
        mock_communicate.return_value = (self._STREAM_OK, "", 0)
        run_cursor_local(
            binary="cursor",
            prompt="hello",
            workspace_root=Path("/tmp/workspace"),
            composer_mode="agent",
            execution_tier="consultative",
        )
        command = mock_communicate.call_args.kwargs["command"]
        self.assertIn("--mode", command)
        self.assertEqual("plan", command[command.index("--mode") + 1])

        mock_communicate.reset_mock()
        run_cursor_local(
            binary="cursor",
            prompt="hello",
            workspace_root=Path("/tmp/workspace"),
            composer_mode="agent",
            execution_tier="executing",
        )
        command = mock_communicate.call_args.kwargs["command"]
        # Cursor CLI rejects --mode agent; executing tier omits the flag.
        self.assertNotIn("--mode", command)


if __name__ == "__main__":
    unittest.main()
