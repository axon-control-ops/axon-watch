from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo.tool_milestone import contextual_tool_fallback  # noqa: E402
from app.kairo.voice_fallback import fallback_for_event  # noqa: E402


class ToolMilestoneTests(unittest.TestCase):
    def test_contextual_read_line_uses_short_file_name(self) -> None:
        line = contextual_tool_fallback(
            "Read services/control-plane/app/research/availability.py",
            operator_prompt="check enrollment availability",
        )
        self.assertIn("availability.py", line or "")
        self.assertIn("Checking", line or "")
        self.assertIn("enrollment", (line or "").lower())

    def test_skips_ambient_orientation_docs(self) -> None:
        self.assertIsNone(contextual_tool_fallback("Read OPERATIONS.md"))
        self.assertIsNone(contextual_tool_fallback("Read README.md"))

    def test_contextual_edit_line(self) -> None:
        line = contextual_tool_fallback("Edit ui/js/auth-bootstrap.js")
        self.assertIn("auth-bootstrap.js", line or "")

    def test_fallback_for_tool_event_uses_contextual_line(self) -> None:
        line = fallback_for_event(
            "tool",
            {
                "tool_label": "Read app/enroll.tsx",
                "operator_prompt": "fix enroll UI",
            },
            [],
            persona_enabled=False,
        )
        self.assertIn("enroll.tsx", line)
        self.assertIn("fix enroll UI", line)
        self.assertNotIn("sir", line.lower())


if __name__ == "__main__":
    unittest.main()
