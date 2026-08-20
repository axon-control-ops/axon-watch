from __future__ import annotations

import sys
import unittest
from pathlib import Path


CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.direct_reply_acceptance import (  # noqa: E402
    evaluate_direct_reply_acceptance,
    narrative_outside_receipts,
)


class DirectReplyAcceptanceTests(unittest.TestCase):
    def test_rejects_dana_style_unclosed_terminal_tail(self) -> None:
        reply = (
            ':::terminal /usr/bin/zsh -lc "sed -n 1,20p README.md"\noutput\n:::\n'
            ':::terminal /usr/bin/zsh -lc "npx tsx -e ..."\n'
            'column preschools.slug does not exist'
        )
        result = evaluate_direct_reply_acceptance(reply)
        self.assertFalse(result.passed)
        self.assertIn("unclosed receipt", result.summary)

    def test_rejects_closed_receipts_without_final_answer(self) -> None:
        reply = ':::terminal pwd\n/workspace\n:::\n:::terminal npm test\npassed\n:::'
        result = evaluate_direct_reply_acceptance(reply)
        self.assertFalse(result.passed)
        self.assertIn("no human-facing conclusion", result.summary)

    def test_accepts_orphan_tool_read_markers_when_final_report_exists(self) -> None:
        reply = (
            ":::terminal npm test\n"
            "sh: 1: jest: not found\n"
            ":::\n"
            ":::tool Read node_modules/.bin/jest\n"
            ":::tool Read node_modules\n"
            "I tried to run the test suite and hit a hard environment blocker.\n\n"
            "Bottom line: this disposable checkout has no installed dependencies."
        )
        result = evaluate_direct_reply_acceptance(reply)
        self.assertTrue(result.passed)
        self.assertIn("hard environment blocker", narrative_outside_receipts(reply))

    def test_accepts_receipts_followed_by_final_answer(self) -> None:
        reply = (
            ':::terminal query\ncount=42\n:::\n'
            'Young Eagles preschool currently has 42 active children.'
        )
        result = evaluate_direct_reply_acceptance(reply)
        self.assertTrue(result.passed)
        self.assertEqual(
            "Young Eagles preschool currently has 42 active children.",
            narrative_outside_receipts(reply),
        )


if __name__ == "__main__":
    unittest.main()
