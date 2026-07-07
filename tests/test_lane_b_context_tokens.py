"""Tests for Lane B editor selection and terminal context blocks."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.lane_b_agent import (  # noqa: E402
    EditorSelectionContext,
    LaneBContext,
    build_lane_b_context_block,
)


class LaneBContextTokenTests(unittest.TestCase):
    @patch("app.chat.lane_b_agent.resolve_workspace_root", return_value=Path("/tmp/ws"))
    @patch("app.chat.lane_b_agent.list_workspace_files", return_value=[])
    def test_build_lane_b_context_block_includes_selection_and_terminal(
        self,
        _mock_files,
        _mock_root,
    ) -> None:
        block = build_lane_b_context_block(
            LaneBContext(
                workspace_id="workspace_axon_watch",
                composer_mode="ask",
                active_file_path="src/app.ts",
                editor_selection=EditorSelectionContext(
                    file_path="src/app.ts",
                    start_line=4,
                    end_line=6,
                    text="const answer = 42;",
                ),
                terminal_snippet="Tests 10 passed",
            )
        )
        self.assertIn("Editor selection (src/app.ts L4-L6):", block)
        self.assertIn("const answer = 42;", block)
        self.assertIn("Terminal output (recent):", block)
        self.assertIn("Tests 10 passed", block)


if __name__ == "__main__":
    unittest.main()
