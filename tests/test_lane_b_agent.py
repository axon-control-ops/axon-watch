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
    should_use_lane_b,
)


class LaneBAgentTests(unittest.TestCase):
    def test_should_use_lane_b_for_ide_modes_only(self) -> None:
        self.assertTrue(should_use_lane_b(composer_mode="ask", command_intent="unsupported"))
        self.assertTrue(should_use_lane_b(composer_mode="plan", command_intent="unsupported"))
        self.assertTrue(should_use_lane_b(composer_mode="agent", command_intent="unsupported"))
        self.assertFalse(should_use_lane_b(composer_mode="command", command_intent="unsupported"))
        self.assertFalse(should_use_lane_b(composer_mode="ask", command_intent="git_status"))

    @patch("app.chat.lane_b_agent._ollama_chat", side_effect=RuntimeError("offline"))
    def test_generate_lane_b_reply_falls_back_when_model_unavailable(self, _mock) -> None:
        reply = generate_lane_b_reply(
            context=LaneBContext(workspace_id="workspace_dashpro", composer_mode="ask"),
            user_prompt="What files are in this repo?",
        )
        self.assertIn("Lane B (ask)", reply)
        self.assertIn("local model bridge is unavailable", reply)


if __name__ == "__main__":
    unittest.main()
