from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.progress_milestones import (  # noqa: E402
    completion_milestone,
    research_milestones_for_delta,
    persist_stream_delta,
    stream_error_milestone,
)


class ChatProgressMilestonesTests(unittest.TestCase):
    def test_research_delta_emits_started_then_complete(self) -> None:
        started = research_milestones_for_delta(
            "",
            ":::research compare axon watch and signal\ncollecting\n",
        )
        self.assertEqual(
            [
                {
                    "event_key": "research_started:0",
                    "event_type": "research_started",
                    "context": {"research_query": "compare axon watch and signal"},
                }
            ],
            started,
        )

        completed = research_milestones_for_delta(
            ":::research compare axon watch and signal\ncollecting\n",
            ":::research compare axon watch and signal\ncollecting\n:::\n",
        )
        self.assertEqual(
            [
                {
                    "event_key": "research_complete:0",
                    "event_type": "research_complete",
                    "context": {"research_query": "compare axon watch and signal"},
                }
            ],
            completed,
        )

    def test_completion_prefers_approval_then_unverified(self) -> None:
        self.assertEqual(
            "approval_required",
            completion_milestone(
                verification_warnings=[],
                run_record={"phase": "awaiting_approval"},
            )["event_type"],
        )
        self.assertEqual(
            "unverified_complete",
            completion_milestone(
                verification_warnings=["missing receipt"],
                run_record={"phase": "completed"},
            )["event_type"],
        )
        self.assertEqual(
            "verified_complete",
            completion_milestone(
                verification_warnings=[],
                run_record={"phase": "completed"},
            )["event_type"],
        )

    def test_stream_error_payload_trims_summary(self) -> None:
        payload = stream_error_milestone("runtime stream failed")
        self.assertEqual("stream_error", payload["event_type"])
        self.assertEqual("runtime stream failed", payload["context"]["failure_summary"])

    def test_stream_delta_redacts_masked_provider_keys_before_persisting(self) -> None:
        leaked = "Incorrect API key provided: sk-admin**************VuSa"
        with patch("app.persistence.chat_store.update_message_content") as update, patch(
            "app.chat.progress_milestones.publish_chat_stream_event"
        ) as publish, patch(
            "app.chat.progress_milestones.publish_research_milestones_for_delta"
        ), patch(
            "app.terminal.agent_job_chat.merge_active_agent_job_terminals",
            side_effect=lambda _message_id, content: content,
        ):
            persisted = persist_stream_delta(
                thread_id="thread-1",
                message_id="message-1",
                previous_content="",
                accumulated=leaked,
                delta=leaked,
                updated_at="2026-08-15T14:00:00Z",
            )

        self.assertEqual("Incorrect API key provided: [REDACTED]", persisted)
        self.assertNotIn("sk-admin", update.call_args.kwargs["content"])
        self.assertNotIn("sk-admin", publish.call_args.args[1]["delta"])


if __name__ == "__main__":
    unittest.main()
