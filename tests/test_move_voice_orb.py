"""Tests for move_voice_orb intent classification and UI action parsing."""

from __future__ import annotations

import unittest

from app.chat.command_intent import classify_command, command_requires_confirmation
from app.chat.command_executor import execute_move_voice_orb
from app.chat.move_voice_orb import move_voice_orb_ack, parse_move_voice_orb_ui_action
from app.kairo.voice_autonomy import resolve_voice_action_tier


class MoveVoiceOrbTests(unittest.TestCase):
    def test_classify_move_orb_phrases(self) -> None:
        self.assertEqual(classify_command("put the orb bottom-left"), "move_voice_orb")
        self.assertEqual(classify_command("move voice orb to top right"), "move_voice_orb")
        self.assertEqual(classify_command("dodge the orb"), "move_voice_orb")

    def test_auto_complete_and_reversible(self) -> None:
        self.assertFalse(command_requires_confirmation("put the orb bottom-left"))
        tier = resolve_voice_action_tier("put the orb bottom-left")
        self.assertEqual(tier.tier, "reversible_auto")
        self.assertTrue(tier.auto_execute)

    def test_parse_ui_action_docks(self) -> None:
        self.assertEqual(
            parse_move_voice_orb_ui_action("put the orb bottom-left"),
            {"type": "move_voice_orb", "dock": "bottom-left"},
        )
        self.assertEqual(
            parse_move_voice_orb_ui_action("dodge the orb"),
            {"type": "move_voice_orb", "mode": "smart_dodge"},
        )

    def test_executor_returns_ui_action(self) -> None:
        result = execute_move_voice_orb("move voice orb to center")
        self.assertTrue(result.success)
        self.assertEqual(result.intent, "move_voice_orb")
        self.assertEqual(result.ui_action, {"type": "move_voice_orb", "dock": "center"})
        self.assertIn("center", move_voice_orb_ack(result.ui_action or {}))


if __name__ == "__main__":
    unittest.main()
