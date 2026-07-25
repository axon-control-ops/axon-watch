from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo.conversation_transcript import log_voice_turn  # noqa: E402


class ConversationTranscriptTests(unittest.TestCase):
    def test_persistence_failure_is_visible_without_losing_reply(self) -> None:
        payload: dict[str, object] = {
            "turn_kind": "chat",
            "reply": "I am still here.",
            "source": "template",
        }

        with patch(
            "app.kairo.conversation_transcript.append_voice_transcript",
            side_effect=OSError("disk unavailable"),
        ), self.assertLogs(
            "app.kairo.conversation_transcript",
            level="WARNING",
        ) as captured:
            returned = log_voice_turn(
                session_id="voice-persistence-failure",
                workspace_id="workspace_alpha",
                raw_content="hello",
                normalized_content="hello",
                payload=payload,
            )

        self.assertIs(payload, returned)
        self.assertIn("voice transcript persistence failed: disk unavailable", captured.output[0])


if __name__ == "__main__":
    unittest.main()
