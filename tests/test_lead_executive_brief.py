"""Executive Lead brief helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.lead_executive_brief import (  # noqa: E402
    executive_next_step,
    looks_like_shell_chore,
    needs_operator_gate,
)


class LeadExecutiveBriefTests(unittest.TestCase):
    def test_shell_chore_stays_with_lead(self) -> None:
        self.assertTrue(
            looks_like_shell_chore("Run from project root .env present, npm run graduation-card-pop-counts")
        )
        next_line = executive_next_step(
            lead_next="Run from project root .env present, npm run graduation-card-pop-counts",
            specialist_name="Cole",
            parent_ask="Count graduation card responses and POP uploads",
            status="completed",
        )
        self.assertIn("I will finish the verification myself", next_line)
        self.assertNotIn("npm run", next_line)
        self.assertNotIn("Ask me", next_line)

    def test_real_gate_asks_operator_with_recommendation(self) -> None:
        next_line = executive_next_step(
            lead_next="decide when to ship the parent notify campaign",
            specialist_name="Priya",
            parent_ask="Ship parent notify",
            status="completed",
        )
        self.assertIn("Decision for you", next_line)
        self.assertIn("My recommendation", next_line)
        self.assertTrue(needs_operator_gate("decide when to ship the parent notify campaign"))


if __name__ == "__main__":
    unittest.main()
