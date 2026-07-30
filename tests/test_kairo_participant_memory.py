from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo_participant_memory import (  # noqa: E402
    apply_participant_address,
    detect_participant_introduction,
    get_active_participant,
    reset_participant_memory_for_tests,
    update_participant_from_utterance,
)
from app.kairo_spoken_symbol_words import strip_literal_symbol_words  # noqa: E402


class SpokenSymbolWordTests(unittest.TestCase):
    def test_strips_literal_symbol_names(self) -> None:
        spoken = strip_literal_symbol_words(
            "Open apps slash console colon forty two with a smiley face"
        )
        self.assertNotIn("slash", spoken.lower())
        self.assertNotIn("colon", spoken.lower())
        self.assertNotIn("smiley", spoken.lower())
        self.assertIn("apps", spoken.lower())
        self.assertIn("console", spoken.lower())


class ParticipantMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_participant_memory_for_tests()

    def tearDown(self) -> None:
        reset_participant_memory_for_tests()

    def test_detects_common_introductions(self) -> None:
        self.assertEqual(detect_participant_introduction("this is Sarah"), "Sarah")
        self.assertEqual(detect_participant_introduction("meet John"), "John")
        self.assertEqual(detect_participant_introduction("say hello to Mary-Jane"), "Mary-Jane")
        self.assertEqual(
            detect_participant_introduction("I'd like you to meet Alex Rivera"),
            "Alex Rivera",
        )

    def test_rejects_blocked_names(self) -> None:
        self.assertIsNone(detect_participant_introduction("this is me"))
        self.assertIsNone(detect_participant_introduction("meet the operator"))

    def test_session_memory_and_clear(self) -> None:
        session = "voice-session-1"
        self.assertEqual(update_participant_from_utterance(session, "this is Sarah"), "Sarah")
        self.assertEqual(get_active_participant(session), "Sarah")
        self.assertIsNone(update_participant_from_utterance(session, "talk to me"))
        self.assertIsNone(get_active_participant(session))

    def test_apply_participant_address_replaces_sir(self) -> None:
        line = apply_participant_address("All set, sir — ready for review.", "Sarah")
        self.assertIn("Sarah", line)
        self.assertNotIn("sir", line.lower())

    def test_agents_use_sir_king_when_no_guest(self) -> None:
        line = apply_participant_address(
            "All set, sir — ready for review.",
            None,
            speaker_kind="agent",
        )
        self.assertIn("Sir King", line)
        self.assertNotRegex(line, r"(?i)\bsir\b(?!\s+king)")

    def test_vaxon_uses_sir_king_when_alone(self) -> None:
        line = apply_participant_address(
            "All set, sir — ready for review.",
            None,
            speaker_kind="vaxon",
        )
        self.assertIn("Sir King", line)
        self.assertNotRegex(line, r"(?i)\bsir\b(?!\s+king)")


if __name__ == "__main__":
    unittest.main()
