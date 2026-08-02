from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo_ask_prompt import build_ask_system_prompt  # noqa: E402


class KairoAskPromptTests(unittest.TestCase):
    def test_persona_enabled_uses_kairo_voice(self) -> None:
        prompt = build_ask_system_prompt(persona_enabled=True)
        self.assertIn("You are VAXON", prompt)
        self.assertIn("Executive Operating System", prompt)
        self.assertIn("Chief of Staff", prompt)
        self.assertIn("Chief Operating Officer", prompt)
        self.assertIn("Mission Commander", prompt)
        self.assertIn("Knowledge Custodian", prompt)
        self.assertIn("Platform Guardian", prompt)
        self.assertIn("Mission Specification", prompt)
        self.assertIn("Evidence Required", prompt)
        self.assertIn("Operator Approved", prompt)
        self.assertIn("read-only", prompt)
        self.assertIn('Address the primary listener as "Sir King"', prompt)
        self.assertNotIn("Lane B", prompt)
        self.assertNotIn("Do NOT use", prompt)

    def test_persona_disabled_uses_neutral_lane_b_copy(self) -> None:
        prompt = build_ask_system_prompt(persona_enabled=False)
        self.assertIn("Lane B in Ask mode", prompt)
        self.assertNotIn("You are KAIRO", prompt)
        self.assertNotIn("You are VAXON", prompt)


if __name__ == "__main__":
    unittest.main()
