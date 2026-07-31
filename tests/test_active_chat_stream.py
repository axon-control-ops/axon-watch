"""Tests for active chat stream target registry."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.terminal.active_chat_stream import (  # noqa: E402
    clear_active_chat_stream,
    get_active_chat_stream,
    register_active_chat_stream,
    reset_active_chat_streams,
)


class ActiveChatStreamTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_active_chat_streams()
        self.addCleanup(reset_active_chat_streams)

    def test_register_lookup_and_clear_by_message(self) -> None:
        register_active_chat_stream(
            workspace_id="workspace_dashpro",
            thread_id="thread_1",
            message_id="message_agent_1",
            run_id="run_1",
        )
        target = get_active_chat_stream("workspace_dashpro")
        assert target is not None
        self.assertEqual("thread_1", target.thread_id)
        self.assertEqual("message_agent_1", target.message_id)
        clear_active_chat_stream(message_id="message_agent_1")
        self.assertIsNone(get_active_chat_stream("workspace_dashpro"))


if __name__ == "__main__":
    unittest.main()
