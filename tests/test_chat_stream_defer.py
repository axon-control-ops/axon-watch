"""Tests for deferred chat stream close while Axon job fences remain open."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.chat_stream_defer import (  # noqa: E402
    finish_chat_stream,
    release_deferred_chat_stream_if_idle,
    reset_deferred_chat_streams,
)
from app.terminal.agent_job_chat import (  # noqa: E402
    close_live_job_fence,
    register_live_job_fence,
    reset_live_job_fences,
)


class ChatStreamDeferTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_deferred_chat_streams()
        reset_live_job_fences()
        self.addCleanup(reset_deferred_chat_streams)
        self.addCleanup(reset_live_job_fences)

    def test_finish_defers_while_open_fence_then_releases(self) -> None:
        register_live_job_fence(
            job_id="agent-job-defer",
            message_id="message_agent_defer",
            command="npm run ota:canary",
        )
        events: list[dict] = []
        closes: list[str] = []

        with (
            mock.patch(
                "app.chat.chat_stream_defer.publish_chat_stream_event",
                side_effect=lambda thread_id, payload: events.append(
                    {"thread_id": thread_id, **payload}
                ),
            ),
            mock.patch(
                "app.chat.chat_stream_defer.close_chat_stream",
                side_effect=lambda thread_id: closes.append(thread_id),
            ),
            mock.patch("app.chat.chat_stream_defer.clear_chat_stream_buffer"),
        ):
            closed_now = finish_chat_stream(
                thread_id="thread_defer",
                message_id="message_agent_defer",
                terminal_payload={
                    "type": "chat_stream_done",
                    "content": "assistant text",
                    "message_id": "message_agent_defer",
                },
            )
            self.assertFalse(closed_now)
            self.assertEqual([], closes)
            self.assertTrue(
                any(item.get("milestone") == "axon_terminal_job_streaming" for item in events)
            )

            close_live_job_fence("agent-job-defer", "message_agent_defer", exit_code=0)
            released = release_deferred_chat_stream_if_idle("message_agent_defer")
            self.assertTrue(released)
            self.assertEqual(["thread_defer"], closes)
            self.assertTrue(any(item.get("type") == "chat_stream_done" for item in events))

    def test_finish_closes_immediately_without_open_fence(self) -> None:
        closes: list[str] = []
        with (
            mock.patch("app.chat.chat_stream_defer.publish_chat_stream_event"),
            mock.patch(
                "app.chat.chat_stream_defer.close_chat_stream",
                side_effect=lambda thread_id: closes.append(thread_id),
            ),
            mock.patch("app.chat.chat_stream_defer.clear_chat_stream_buffer"),
        ):
            closed_now = finish_chat_stream(
                thread_id="thread_now",
                message_id="message_now",
                terminal_payload={"type": "chat_stream_done", "content": "done"},
            )
            self.assertTrue(closed_now)
            self.assertEqual(["thread_now"], closes)


if __name__ == "__main__":
    unittest.main()
