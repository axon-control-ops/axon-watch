from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.cursor_stream_events import (  # noqa: E402
    CursorStreamAssembler,
    _tool_block_from_event,
    assistant_text_delta,
)


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


class CursorStreamPartialDedupeTests(unittest.TestCase):
    def test_assistant_text_delta_skips_duplicate_final_event(self) -> None:
        self.assertEqual("hello", assistant_text_delta("", "hello"))
        self.assertEqual(" world", assistant_text_delta("hello", " world"))
        self.assertEqual("", assistant_text_delta("hello world", "hello world"))
        self.assertEqual("", assistant_text_delta("hello world", "hello"))

    def test_assistant_text_delta_skips_echoed_cumulative_prefix(self) -> None:
        sentence = (
            "The built-in web lookup path was not available, so I am checking the audited path."
        )
        self.assertEqual("", assistant_text_delta(sentence, sentence + sentence))

    def test_stream_assembler_does_not_duplicate_partial_and_final_text(self) -> None:
        assembler = CursorStreamAssembler()
        events = [
            '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"hello"}]}}',
            '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":" world"}]}}',
            '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"hello world"}]}}',
            '{"type":"result","subtype":"success","is_error":false,"result":"hello world"}',
        ]
        for line in events:
            assembler.feed_line(line)
        self.assertEqual("hello world", assembler.finalize())

    def test_finalize_does_not_reappend_result_when_assistant_text_exists(self) -> None:
        assembler = CursorStreamAssembler()
        assembler.feed_line(
            '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"done"}]}}'
        )
        assembler.feed_line(
            '{"type":"result","subtype":"success","is_error":false,"result":"done"}'
        )
        self.assertEqual("done", assembler.finalize())


if __name__ == "__main__":
    unittest.main()
