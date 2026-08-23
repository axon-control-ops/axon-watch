from __future__ import annotations

import sys
import unittest
from pathlib import Path


CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.lane_b_persona_fast_path import build_ambiguous_reply_guard  # noqa: E402


class AmbiguousReplyGuardTests(unittest.TestCase):
    def test_blocks_bare_number_without_recovering_history(self) -> None:
        reply = build_ambiguous_reply_guard(" 2 ")
        self.assertIsNotNone(reply)
        assert reply is not None
        self.assertIn("No task, handoff, command, or file change was created", reply)

    def test_does_not_block_a_real_instruction(self) -> None:
        self.assertIsNone(build_ambiguous_reply_guard("Assign Tess the privacy migration plan"))

    def test_does_not_block_a_bare_year(self) -> None:
        self.assertIsNone(build_ambiguous_reply_guard("2026"))


if __name__ == "__main__":
    unittest.main()
