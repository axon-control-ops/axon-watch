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
)
from app.cli_runtime.research_stream_blocks import (  # noqa: E402
    dedupe_assistant_paragraphs,
    dedupe_research_blocks,
    ensure_research_blocks_in_content,
    normalize_transcript_content,
    research_block_from_tool_call,
    research_started_block_from_event,
    sanitize_research_block_bodies_in_content,
)
from app.research.availability import format_capability_line, research_capability_snapshot  # noqa: E402


def _web_search_event(query: str, results: list[dict[str, str]]) -> dict:
    return {
        "type": "tool_call",
        "subtype": "completed",
        "tool_call": {
            "webSearchToolCall": {
                "args": {"query": query},
                "result": {"success": {"results": results}},
            }
        },
    }


def _mcp_search_event(query: str, payload: dict[str, object]) -> dict:
    return {
        "type": "tool_call",
        "subtype": "completed",
        "tool_call": {
            "mcpToolCall": {
                "args": {
                    "tool": "axon_research_search",
                    "arguments": {"query": query},
                },
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(payload),
                        }
                    ]
                },
            }
        },
    }


class CursorStreamResearchBlockTests(unittest.TestCase):
    def test_web_search_renders_research_cards(self) -> None:
        block = _tool_block_from_event(
            _web_search_event(
                "vite configuration",
                [
                    {
                        "title": "Vite Guide",
                        "url": "https://vitejs.dev/guide/",
                        "snippet": "Official documentation.",
                    }
                ],
            ),
            "",
        )
        self.assertIn(":::research vite configuration", block)
        self.assertIn("- Vite Guide | https://vitejs.dev/guide/", block)
        self.assertIn("Official documentation.", block)
        self.assertTrue(block.rstrip().endswith(":::"))

    def test_web_search_without_results_still_renders_query(self) -> None:
        block = _tool_block_from_event(_web_search_event("react hooks", []), "")
        self.assertIn(":::research react hooks", block)
        self.assertTrue(block.rstrip().endswith(":::"))

    def test_mcp_axon_research_search_renders_research_cards(self) -> None:
        block = research_block_from_tool_call(
            _mcp_search_event(
                "cursor cli web tools",
                {
                    "success": True,
                    "query": "cursor cli web tools",
                    "provider": "duckduckgo_instant",
                    "results": [
                        {
                            "title": "Cursor CLI",
                            "url": "https://cursor.com/docs/cli/overview",
                            "snippet": "Headless agent CLI.",
                        }
                    ],
                },
            )["tool_call"],
        )
        self.assertIn(":::research cursor cli web tools", block)
        self.assertIn("- Cursor CLI | https://cursor.com/docs/cli/overview", block)

    def test_mcp_fetch_payload_renders_single_source_card(self) -> None:
        event = {
            "type": "tool_call",
            "subtype": "completed",
            "tool_call": {
                "mcpToolCall": {
                    "args": {
                        "toolName": "axon_research_fetch",
                        "arguments": {"url": "https://example.com/"},
                    },
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "success": True,
                                        "url": "https://example.com/",
                                        "title": "example.com",
                                        "content": "Example Domain",
                                    }
                                ),
                            }
                        ]
                    },
                }
            },
        }
        block = _tool_block_from_event(event, "")
        self.assertIn(":::research https://example.com/", block)
        self.assertIn("Example Domain", block)

    def test_started_then_completed_research_stream(self) -> None:
        assembler = CursorStreamAssembler()
        started = {
            "type": "tool_call",
            "subtype": "started",
            "tool_call": {
                "mcpToolCall": {
                    "args": {
                        "tool": "axon_research_search",
                        "arguments": {"query": "vite configuration"},
                    }
                }
            },
        }
        completed = _mcp_search_event(
            "vite configuration",
            {
                "success": True,
                "results": [
                    {
                        "title": "Vite",
                        "url": "https://vitejs.dev/",
                        "snippet": "Next generation frontend tooling.",
                    }
                ],
            },
        )
        assembler.feed_line(json.dumps(started))
        assembler.feed_line(json.dumps(completed))
        content = assembler.finalize()
        self.assertEqual(1, content.count(":::research vite configuration"))
        self.assertIn("- Vite | https://vitejs.dev/", content)
        self.assertTrue(content.rstrip().endswith(":::"))

    def test_started_without_args_waits_for_completed_header(self) -> None:
        assembler = CursorStreamAssembler()
        started = {
            "type": "tool_call",
            "subtype": "started",
            "tool_call": {
                "mcpToolCall": {
                    "args": {
                        "tool": "axon_research_search",
                    }
                }
            },
        }
        completed = _mcp_search_event(
            "what is today's date",
            {
                "success": True,
                "results": [
                    {
                        "title": "Time",
                        "url": "https://time.is/",
                        "snippet": "Tuesday",
                    }
                ],
            },
        )
        assembler.feed_line(json.dumps(started))
        assembler.feed_line(json.dumps(completed))
        content = assembler.finalize()
        self.assertEqual(1, content.count(":::research"))
        self.assertIn("what is today's date", content)
        self.assertNotIn("axon research search", content.lower())

    def test_started_event_opens_live_research_block(self) -> None:
        event = {
            "type": "tool_call",
            "subtype": "started",
            "tool_call": {
                "webSearchToolCall": {"args": {"query": "live query"}},
            },
        }
        block = research_started_block_from_event(event)
        self.assertEqual("\n:::research live query\n", block)

    def test_started_without_query_args_is_suppressed(self) -> None:
        event = {
            "type": "tool_call",
            "subtype": "started",
            "tool_call": {
                "mcpToolCall": {"args": {"tool": "axon_research_search"}},
            },
        }
        self.assertEqual("", research_started_block_from_event(event))

    def test_dedupe_research_headers(self) -> None:
        raw = "\n".join(
            [
                ":::research axon research search",
                ":::research what is today's date",
                "- Time | https://time.is/",
                "Tuesday",
                ":::",
            ]
        )
        deduped = dedupe_research_blocks(raw)
        self.assertEqual(1, deduped.count(":::research"))
        self.assertIn("what is today's date", deduped)
        self.assertIn("- Time | https://time.is/", deduped)

    def test_dedupe_assistant_paragraphs(self) -> None:
        paragraph = "The built-in web lookup path was not available."
        raw = f"{paragraph}\n\n{paragraph}"
        self.assertEqual(paragraph, dedupe_assistant_paragraphs(raw))

    def test_dedupe_assistant_paragraphs_preserves_thinking_blocks(self) -> None:
        raw = "\n".join(
            [
                ":::thinking",
                "Checking the file.",
                ":::",
                "Same line.",
                "Same line.",
                ":::tool Read README.md",
            ]
        )
        deduped = dedupe_assistant_paragraphs(raw)
        self.assertIn(":::thinking\nChecking the file.\n:::", deduped)
        self.assertEqual(1, deduped.count("Same line."))
        self.assertIn(":::tool Read README.md", deduped)

    def test_dedupe_assistant_paragraphs_after_thinking_gap(self) -> None:
        line = (
            "Running the August billing dry-run and verifying deployment state "
            "from the prior session."
        )
        raw = "\n".join(
            [
                ":::thinking",
                "Planning next steps.",
                ":::",
                line,
                line,
                "",
                ":::tool Read scripts/backfill-young-eagles-missing-tuition.ts",
            ]
        )
        deduped = dedupe_assistant_paragraphs(raw)
        self.assertEqual(1, deduped.count(line))
        self.assertIn(":::tool Read scripts/backfill-young-eagles-missing-tuition.ts", deduped)

    def test_normalize_transcript_content_collapses_duplicates(self) -> None:
        raw = "\n".join(
            [
                ":::research news headlines today",
                ":::research news headlines today",
                "- BBC | https://www.bbc.com/news",
                "Headlines",
                ":::",
                "Same answer.",
                "",
                "Same answer.",
            ]
        )
        normalized = normalize_transcript_content(raw)
        self.assertEqual(1, normalized.count(":::research news headlines today"))
        self.assertEqual(1, normalized.count("Same answer."))

    def test_normalize_transcript_content_drops_repeated_prose_across_blocks(self) -> None:
        raw = "\n".join(
            [
                "Here is the answer.",
                "",
                ":::tool Read README.md",
                "",
                "Here is the answer.",
                "",
                "More details.",
            ]
        )
        normalized = normalize_transcript_content(raw)
        self.assertEqual(1, normalized.count("Here is the answer."))
        self.assertIn("More details.", normalized)
        self.assertIn(":::tool Read README.md", normalized)

    def test_generic_tool_research_label_is_upgraded(self) -> None:
        content = "Answer\n:::tool Axon research search cursor cli\nMore text"
        upgraded = ensure_research_blocks_in_content(content)
        self.assertIn(":::research cursor cli", upgraded)
        self.assertNotIn(":::tool Axon research", upgraded)

    def test_capability_line_requires_audited_tools(self) -> None:
        line = format_capability_line(research_capability_snapshot())
        self.assertIn("axon_research_search", line)
        self.assertIn("headless runtime", line)

    def test_truncated_mcp_envelope_snippet_is_sanitized(self) -> None:
        truncated = (
            "[{'text': {'text': '{\\n  \"success\": true,\\n  "
            '"query": "react hooks",\\n  "provider": "duckduckgo_instant",\\n  '
            '"results": [],\\n  "count": 0,\\n  "receipt": {\\n    "kind": "search"'
        )
        raw = "\n".join(
            [
                ":::research Web search",
                "- No web results | about:blank",
                truncated,
                ":::",
            ]
        )
        normalized = sanitize_research_block_bodies_in_content(raw)
        self.assertIn("react hooks", normalized)
        self.assertNotIn("[{'text'", normalized)

    def test_mcp_search_empty_results_do_not_emit_raw_envelope(self) -> None:
        block = research_block_from_tool_call(
            _mcp_search_event(
                "empty search",
                {
                    "success": True,
                    "query": "empty search",
                    "provider": "duckduckgo_instant",
                    "results": [],
                },
            )["tool_call"],
        )
        self.assertIn("No web results", block)
        self.assertIn("@provider duckduckgo_instant", block)
        self.assertIn("@kind search", block)
        self.assertNotIn("[{'text'", block)
        self.assertNotIn('{"success"', block)


if __name__ == "__main__":
    unittest.main()
