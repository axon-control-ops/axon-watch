"""Debug-mode system prompt (Cursor-style evidence loop)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.debug_prompt import build_debug_system_prompt  # noqa: E402


class DebugPromptTests(unittest.TestCase):
    def test_executing_prompt_covers_evidence_loop(self) -> None:
        prompt = build_debug_system_prompt(execution_tier="executing")
        self.assertIn("Debug mode with Full Access", prompt)
        self.assertIn("hypotheses", prompt.lower())
        self.assertIn(".axon/debug-session.ndjson", prompt)
        self.assertIn("Reproduce", prompt)
        self.assertIn(":::debug-reproduce", prompt)
        self.assertIn("targeted fix", prompt.lower())
        self.assertIn("remove instrumentation", prompt.lower())

    def test_consultative_prompt_blocks_claimed_edits(self) -> None:
        prompt = build_debug_system_prompt(execution_tier="consultative")
        self.assertIn("consultative", prompt.lower())
        self.assertIn("Do not claim you edited files", prompt)
        self.assertIn("Full Access", prompt)


if __name__ == "__main__":
    unittest.main()
