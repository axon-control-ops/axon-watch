from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.cursor_stream_events import (  # noqa: E402
    CursorStreamAssembler,
    _tool_block_from_event,
    assistant_text_delta,
    terminal_started_block_from_event,
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


def _shell_started_event(command: str) -> dict:
    return {
        "type": "tool_call",
        "subtype": "started",
        "tool_call": {
            "shellToolCall": {
                "args": {"command": command},
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

    def test_shell_started_opens_live_terminal_block(self) -> None:
        block = terminal_started_block_from_event(_shell_started_event("npm test"))
        self.assertEqual("\n:::terminal npm test\n", block)
        self.assertFalse(block.rstrip().endswith(":::"))

    def test_assembler_opens_then_closes_terminal_without_duplicate(self) -> None:
        assembler = CursorStreamAssembler()
        import json

        assembler.feed_line(json.dumps(_shell_started_event("sleep 5")))
        self.assertIn(":::terminal sleep 5", assembler.content)
        self.assertFalse(assembler.content.rstrip().endswith(":::"))
        assembler.feed_line(
            json.dumps(_shell_event("sleep 5", "done"))
        )
        finalized = assembler.finalize()
        self.assertEqual(finalized.count(":::terminal sleep 5"), 1)
        self.assertIn("done", finalized)
        self.assertTrue(finalized.rstrip().endswith(":::") or ":::terminal" in finalized)


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

    def test_assistant_text_delta_skips_near_duplicate_thinking_prefix(self) -> None:
        body = (
            "got the current README and the local setup docs open. "
            "I'm going to turn the root guide into a cleaner day-to-day entry point."
        )
        self.assertEqual("", assistant_text_delta(f"'ve {body}", f"I've {body}"))
        self.assertEqual("", assistant_text_delta(f"I've {body}", f"'ve {body}"))

    def test_assistant_text_delta_skips_formatted_debug_aggregate(self) -> None:
        plain = (
            "Ranked hypotheses for*server recovery**:\n"
            "1.*H1* — The stream was interrupted.\n"
            "2.*H2* — The run mode was reset.\n"
            "3.*H3* — The server identity changed.\n"
            "4.*H4* — The transcript was duplicated.\n"
            "5.*H5* — The UI lost its linked run.\n\n"
            ":::debug-reproduce\n1. Restart the server.\n2. Observe recovery.\n:::"
        )
        formatted = (
            "Ranked hypotheses for **server recovery**:\n"
            "1. **H1** — The stream was interrupted.\n"
            "2. **H2** — The run mode was reset.\n"
            "3. **H3** — The server identity changed.\n"
            "4. **H4** — The transcript was duplicated.\n"
            "5. **H5** — The UI lost its linked run.\n\n"
            ":::debug-reproduce\n1. Restart the server.\n2. Observe recovery.\n:::"
        )
        self.assertEqual("", assistant_text_delta(plain, formatted))

    def test_assistant_text_delta_skips_glued_partial_section_echo(self) -> None:
        opener = (
            "No — that Working with starter line does not need to sit in the composer. "
            "Talk already introduces the teammate. The composer should stay clear for the real ask."
        )
        day_to_day = "\n".join(
            [
                "**Day-to-day with Agents**",
                "1. Open Team in the left bar — each person owns a slice of the business.",
                "2. Working agents glow; they can speak a short status when you engage them.",
                "3. Click a teammate, then type what you need in the composer.",
                "4. Approve when Full Access asks; watch the dock for progress and handoffs.",
                "5. Lead for priorities, Night Watch for signals — that is the daily loop.",
            ]
        )
        good = f"{opener}\n\n{day_to_day}"
        echo = f"{opener}\n\n{day_to_day}"
        self.assertEqual("", assistant_text_delta(good, echo))
        # Glued append path: stream concatenates without a separator.
        self.assertEqual("", assistant_text_delta(good, echo))
        from app.cli_runtime.research_stream_blocks import collapse_duplicated_body

        collapsed = collapse_duplicated_body(good + echo)
        self.assertEqual(good.strip(), collapsed.strip())

    def test_stream_assembler_does_not_duplicate_thinking_echo(self) -> None:
        assembler = CursorStreamAssembler()
        thought = (
            "I found the one concrete breakage left behind: the new teacher dashboard "
            "tests aren't mocking useWindowDimensions."
        )
        events = [
            json.dumps({"type": "thinking", "subtype": "delta", "text": thought[:24]}),
            json.dumps({"type": "thinking", "subtype": "delta", "text": thought}),
            json.dumps({"type": "thinking", "subtype": "delta", "text": thought + thought}),
            json.dumps({"type": "thinking", "subtype": "completed"}),
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "DONE"}],
                    },
                }
            ),
        ]
        for line in events:
            assembler.feed_line(line)
        content = assembler.finalize()
        self.assertEqual(content.count(thought), 1)
        self.assertIn(f":::thinking\n{thought}\n:::", content)
        self.assertTrue(content.endswith("DONE"))

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
