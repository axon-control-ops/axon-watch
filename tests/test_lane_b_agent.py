"""Tests for Lane B composer routing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.lane_b_agent import (  # noqa: E402
    LaneBContext,
    generate_lane_b_reply,
    generate_lane_b_result,
    should_use_lane_b,
)


class LaneBAgentTests(unittest.TestCase):
    def test_should_use_lane_b_for_ide_modes_only(self) -> None:
        self.assertTrue(should_use_lane_b(composer_mode="ask", command_intent="unsupported"))
        self.assertTrue(should_use_lane_b(composer_mode="plan", command_intent="unsupported"))
        self.assertTrue(should_use_lane_b(composer_mode="agent", command_intent="unsupported"))
        self.assertTrue(should_use_lane_b(composer_mode="debug", command_intent="unsupported"))
        self.assertFalse(should_use_lane_b(composer_mode="command", command_intent="unsupported"))

    def test_executing_tier_prompt_authorizes_edits(self) -> None:
        from app.cli_runtime.router import _build_prompt

        executing = _build_prompt(
            composer_mode="agent",
            user_prompt="edit the file",
            context_block="ctx",
            execution_tier="executing",
        )
        self.assertIn("approved execution access", executing)
        self.assertIn("edit files", executing.lower())
        self.assertIn("audited commands", executing.lower())
        self.assertIn("Reply in first person", executing)
        self.assertNotIn("consultative", executing.lower())

        consultative = _build_prompt(
            composer_mode="agent",
            user_prompt="edit the file",
            context_block="ctx",
            execution_tier="consultative",
        )
        self.assertIn("consultative", consultative.lower())
        self.assertIn("do not claim", consultative.lower())
        self.assertIn("Reply in first person", consultative)

        ask = _build_prompt(
            composer_mode="ask",
            user_prompt="what is this?",
            context_block="ctx",
        )
        self.assertIn("Reply in first person", ask)

        plan = _build_prompt(
            composer_mode="plan",
            user_prompt="figure out the next changes",
            context_block="ctx",
        )
        self.assertIn(
            "When external or vendor facts are required, call axon_research_search",
            plan,
        )
        self.assertIn("Online research", plan)
        self.assertIn("Produce a complete durable plan", plan)
        self.assertIn("## Verification checklist", plan)
        self.assertIn("Reply in first person", plan)

        debug = _build_prompt(
            composer_mode="debug",
            user_prompt="this button does nothing",
            context_block="ctx",
            execution_tier="executing",
        )
        self.assertIn("Debug mode with Full Access", debug)
        self.assertIn(".axon/debug-session.ndjson", debug)
        self.assertIn("hypotheses", debug.lower())
        self.assertIn("Reply in first person", debug)

    def test_sentry_requests_receive_secret_free_watch_monitor_evidence(self) -> None:
        from app.cli_runtime.router import _build_prompt

        monitors = {
            "items": [
                {
                    "check_type": "sentry_recent_issues",
                    "status": "critical",
                    "detail": "Sentry returned 1 unresolved issue(s), 58 event(s)",
                    "issues": [
                        {
                            "short_id": "EDUDASHPRO-5Z",
                            "title": "Realtime callback error",
                            "count": 58,
                            "permalink": "https://example.invalid/issues/5Z/",
                        }
                    ],
                }
            ]
        }
        with patch("app.cli_runtime.router.fetch_watch_monitors", return_value=monitors):
            prompt = _build_prompt(
                composer_mode="agent",
                user_prompt="Check VAXON's Sentry reports",
                context_block="ctx",
                execution_tier="executing",
            )

        self.assertIn("trusted Axon Watch monitor evidence", prompt)
        self.assertIn("EDUDASHPRO-5Z", prompt)
        self.assertIn("Realtime callback error", prompt)
        self.assertIn("Do not inspect .env", prompt)
        self.assertNotIn("SENTRY_AUTH_TOKEN=", prompt)

    def test_ide_modes_keep_lane_b_even_when_prompt_matches_command_keywords(self) -> None:
        # "Add a comment to README.md" must not become an operator read_file run.
        self.assertTrue(should_use_lane_b(composer_mode="ask", command_intent="git_status"))
        self.assertTrue(should_use_lane_b(composer_mode="agent", command_intent="read_file"))
        self.assertTrue(should_use_lane_b(composer_mode="plan", command_intent="list_files"))
        self.assertFalse(should_use_lane_b(composer_mode="command", command_intent="read_file"))

    @patch(
        "app.chat.lane_b_agent.dispatch_ide_composer",
        return_value={
            "content": "Runtime reply",
            "dispatched": True,
            "runtime_id": "cursor_local",
            "runtime_label": "Cursor CLI (local)",
            "reason": "",
        },
    )
    def test_generate_lane_b_reply_uses_runtime_router(self, mock_dispatch) -> None:
        reply = generate_lane_b_reply(
            context=LaneBContext(workspace_id="workspace_dashpro", composer_mode="ask"),
            user_prompt="What files are in this repo?",
        )
        self.assertEqual("Runtime reply", reply)
        mock_dispatch.assert_called_once()

    @patch("app.chat.lane_b_agent.dispatch_ide_composer", side_effect=RuntimeError("offline"))
    def test_generate_lane_b_reply_falls_back_when_runtime_unavailable(self, _mock_dispatch) -> None:
        reply = generate_lane_b_reply(
            context=LaneBContext(workspace_id="workspace_dashpro", composer_mode="ask"),
            user_prompt="What files are in this repo?",
        )
        self.assertIn("Lane B (ask)", reply)
        self.assertIn("is unavailable", reply)
        self.assertIn("Check Runtime or `/vault`, then retry.", reply)

    @patch(
        "app.chat.lane_b_agent.dispatch_ide_composer",
        return_value={
            "content": "Runtime reply",
            "dispatched": True,
            "runtime_id": "cursor_local",
            "runtime_label": "Cursor CLI (local)",
            "reason": "",
            "mcp_tools": {
                "count": 2,
                "items": [
                    {"id": "workspace_files.read", "mode_support": ["ask", "plan", "agent"]},
                    {"id": "runs.history", "mode_support": ["plan", "agent"]},
                ],
            },
        },
    )
    def test_generate_lane_b_result_exposes_dispatch_metadata(self, mock_dispatch) -> None:
        result = generate_lane_b_result(
            context=LaneBContext(workspace_id="workspace_dashpro", composer_mode="agent"),
            user_prompt="Implement the next step.",
        )
        self.assertEqual("Runtime reply", result["content"])
        self.assertTrue(result["dispatched"])
        self.assertEqual("cursor_local", result["runtime_id"])
        mcp_tools = result.get("mcp_tools")
        self.assertIsInstance(mcp_tools, dict)
        self.assertGreaterEqual(mcp_tools.get("count"), 1)
        mock_dispatch.assert_called_once()

    @patch("app.chat.lane_b_agent.try_lane_b_git_commit_dispatch")
    @patch(
        "app.chat.lane_b_agent.dispatch_ide_composer",
        return_value={"content": "Worker reply", "dispatched": True},
    )
    def test_worker_prompt_skips_direct_git_dispatch(self, mock_dispatch, mock_git) -> None:
        result = generate_lane_b_result(
            context=LaneBContext(workspace_id="workspace_axon_watch", composer_mode="agent"),
            user_prompt="Do not commit, push, or merge. End with Confidence: N/10.",
            execution_access="full",
            allow_git_dispatch=False,
        )
        self.assertEqual("Worker reply", result["content"])
        mock_git.assert_not_called()
        mock_dispatch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
