from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.cursor_stream_events import _tool_block_from_event  # noqa: E402


def _shell_event(command: str, stdout: str = "") -> dict:
    return {
        "type": "tool_call",
        "subtype": "completed",
        "tool_call": {
            "shellToolCall": {
                "args": {"command": command},
                "result": {"success": {"stdout": stdout}},
            }
        },
    }


class CursorStreamTerminalBlockTests(unittest.TestCase):
    def test_shell_tool_call_renders_terminal_block(self) -> None:
        block = _tool_block_from_event(_shell_event("git status", "On branch dev"), "")
        self.assertIn(":::terminal git status", block)
        self.assertIn("On branch dev", block)
        self.assertTrue(block.rstrip().endswith(":::"))

    def test_shell_tool_call_without_output_still_renders(self) -> None:
        block = _tool_block_from_event(_shell_event("mkdir -p build"), "")
        self.assertIn(":::terminal mkdir -p build", block)
        self.assertTrue(block.rstrip().endswith(":::"))

    def test_long_output_is_truncated(self) -> None:
        block = _tool_block_from_event(_shell_event("cat big.log", "x" * 9000), "")
        self.assertIn("(output truncated)", block)

    def test_read_tool_call_keeps_tool_block(self) -> None:
        event = {
            "type": "tool_call",
            "subtype": "completed",
            "tool_call": {"readToolCall": {"args": {"path": "README.md"}}},
        }
        block = _tool_block_from_event(event, "")
        self.assertIn(":::tool Read README.md", block)


if __name__ == "__main__":
    unittest.main()
