from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.lane_b_thread_context import build_lane_b_thread_context_appendix  # noqa: E402


class LaneBThreadContextTests(unittest.TestCase):
    def test_packs_recent_operator_and_agent_turns(self) -> None:
        appendix = build_lane_b_thread_context_appendix(
            [
                {"role": "system", "content": "noise"},
                {"role": "operator", "content": "Polish the teacher dashboard"},
                {"role": "agent", "content": "Working on TeacherDashboardSecondaryMenu"},
                {"role": "operator", "content": "Yes please continue there"},
            ]
        )
        self.assertIn("Recent IDE thread", appendix)
        self.assertIn("teacher dashboard", appendix)
        self.assertIn("TeacherDashboardSecondaryMenu", appendix)
        self.assertIn("Yes please continue there", appendix)
        self.assertNotIn("noise", appendix)

    def test_skips_empty_agent_placeholders(self) -> None:
        appendix = build_lane_b_thread_context_appendix(
            [
                {"role": "operator", "content": "hello"},
                {"role": "agent", "content": "   "},
            ]
        )
        self.assertIn("operator: hello", appendix)
        self.assertNotIn("agent:", appendix)

    def test_caps_message_count_and_chars(self) -> None:
        messages = [
            {"role": "operator", "content": f"turn-{index} " + ("x" * 40)}
            for index in range(10)
        ]
        appendix = build_lane_b_thread_context_appendix(
            messages,
            max_messages=3,
            max_chars=120,
        )
        self.assertIn("turn-8", appendix)
        self.assertNotIn("turn-0", appendix)
        self.assertTrue(appendix.endswith("…"))
        self.assertLessEqual(len(appendix), 120)


if __name__ == "__main__":
    unittest.main()
