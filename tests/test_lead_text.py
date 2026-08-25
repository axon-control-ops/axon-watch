from __future__ import annotations

import sys
import unittest
from pathlib import Path


CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.lead_text import lead_summary_from_reply  # noqa: E402


class LeadTextTests(unittest.TestCase):
    def test_summary_uses_final_narrative_not_first_terminal_receipt(self) -> None:
        reply = (
            ':::terminal sed -n 1,20p README.md\nREADME output\n:::\n'
            'Young Eagles has 58 active children; 56 are billable and non-test.\n\n'
            'Confidence: 10/10'
        )
        self.assertEqual(
            'Young Eagles has 58 active children; 56 are billable and non-test.',
            lead_summary_from_reply(reply),
        )

    def test_summary_reports_missing_narrative(self) -> None:
        self.assertIn(
            "No verified final narrative",
            lead_summary_from_reply(':::terminal pwd\n/workspace\n:::'),
        )


if __name__ == "__main__":
    unittest.main()
