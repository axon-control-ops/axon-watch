"""Tests for persisted VAXON voice transcript log."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store  # noqa: E402
from app.persistence.voice_transcript_store import (  # noqa: E402
    append_voice_transcript,
    list_recent_spoken_lines,
    list_recent_voice_transcripts,
)


class VoiceTranscriptStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_append_and_list_voice_transcripts(self) -> None:
        append_voice_transcript(
            session_id="session_a",
            raw_content="hey vixen check health",
            normalized_content="hey VAXON check health",
            reply="On it — Run ./scripts/dev/check-health.sh.",
            turn_kind="command",
            source="template",
            workspace_id="workspace_axon_watch",
            stt_note="stt_normalized",
            duration_ms=187,
            runtime_dispatched=False,
            submission_intent="ask",
        )
        entries = list_recent_voice_transcripts(limit=5)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["normalized_content"], "hey VAXON check health")
        self.assertEqual(entries[0]["stt_note"], "stt_normalized")
        self.assertEqual(entries[0]["duration_ms"], 187)
        self.assertEqual(entries[0]["runtime_dispatched"], 0)
        self.assertEqual(entries[0]["submission_intent"], "ask")

    def test_list_recent_voice_transcripts_filters_by_session(self) -> None:
        append_voice_transcript(
            session_id="session_a",
            raw_content="status",
            normalized_content="status",
            reply="All clear.",
            turn_kind="conversation_reply",
            source="fallback",
        )
        append_voice_transcript(
            session_id="session_b",
            raw_content="brief me",
            normalized_content="brief me",
            reply="DashPro still needs review.",
            turn_kind="briefing",
            source="model",
        )
        entries = list_recent_voice_transcripts(limit=5, session_id="session_b")
        self.assertEqual(1, len(entries))
        self.assertEqual("session_b", entries[0]["session_id"])
        self.assertEqual("DashPro still needs review.", entries[0]["reply"])

    def test_list_recent_spoken_lines_dedupes_across_event_types(self) -> None:
        append_voice_transcript(
            session_id="session_shared",
            raw_content="any approvals?",
            normalized_content="any approvals?",
            reply="Two approvals waiting.",
            turn_kind="conversation_reply",
            source="fallback",
        )
        append_voice_transcript(
            session_id="session_shared",
            raw_content="conversation_reply",
            normalized_content="conversation_reply",
            reply="Two approvals waiting.",
            turn_kind="conversation_reply",
            source="model",
        )
        append_voice_transcript(
            session_id="session_shared",
            raw_content="briefing",
            normalized_content="briefing",
            reply="DashPro is still the top signal.",
            turn_kind="briefing",
            source="fallback",
        )
        self.assertEqual(
            [
                "Two approvals waiting.",
                "DashPro is still the top signal.",
            ],
            list_recent_spoken_lines(session_id="session_shared", limit=5),
        )


if __name__ == "__main__":
    unittest.main()
