from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.cursor_stream_events import _tool_block_from_event  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
