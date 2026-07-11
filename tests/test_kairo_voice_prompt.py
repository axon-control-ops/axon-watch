from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo_voice_prompt import (  # noqa: E402
    KAIRO_CONVERSATION_VOICE_SYSTEM,
    KAIRO_VOICE_SYSTEM,
    build_speak_user_prompt,
    filter_speak_context,
)


class KairoVoicePromptTests(unittest.TestCase):
    def test_filter_drops_stale_active_file(self) -> None:
        filtered = filter_speak_context(
            "agent_start",
            {
                "active_file": "README.md",
                "operator_prompt": "What does the project need?",
                "full_access": True,
            },
        )
        self.assertNotIn("active_file", filtered)
        self.assertEqual(filtered["operator_prompt"], "What does the project need?")

    def test_build_prompt_omits_readme_from_agent_start(self) -> None:
        prompt = build_speak_user_prompt(
            event_type="agent_start",
            context={
                "active_file": "README.md",
                "operator_prompt": "fix the terminal",
                "full_access": True,
            },
            recent_lines=[],
        )
        self.assertIn("operator_prompt: fix the terminal", prompt)
        self.assertNotIn("README", prompt)

    def test_voice_system_requires_sir_and_blocks_symbol_speech(self) -> None:
        self.assertIn('Address the primary listener as "sir"', KAIRO_VOICE_SYSTEM)
        self.assertIn("introduced someone else by name", KAIRO_VOICE_SYSTEM)
        self.assertIn("colon", KAIRO_VOICE_SYSTEM.lower())
        self.assertIn("smiley face", KAIRO_VOICE_SYSTEM.lower())
        self.assertNotIn("Do NOT use", KAIRO_VOICE_SYSTEM)
        self.assertIn('Address the primary listener as "sir"', KAIRO_CONVERSATION_VOICE_SYSTEM)

    def test_guest_name_appears_in_speak_prompt(self) -> None:
        prompt = build_speak_user_prompt(
            event_type="conversation_reply",
            context={
                "reply": "Systems are nominal.",
                "guest_name": "Sarah",
            },
            recent_lines=[],
        )
        self.assertIn("guest_name: Sarah", prompt)
        self.assertIn("Addressing: speak to Sarah by name", prompt)


if __name__ == "__main__":
    unittest.main()
