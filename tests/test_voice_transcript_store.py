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
        )
        entries = list_recent_voice_transcripts(limit=5)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["normalized_content"], "hey VAXON check health")
        self.assertEqual(entries[0]["stt_note"], "stt_normalized")


if __name__ == "__main__":
    unittest.main()
