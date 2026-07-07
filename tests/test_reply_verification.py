from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.reply_verification import (  # noqa: E402
    scan_unverified_claims,
    verify_lane_b_reply,
)
from app.cli_runtime.router import _fallback_reply  # noqa: E402


class ReplyVerificationTests(unittest.TestCase):
    def test_flags_consultative_execution_claims(self) -> None:
        warnings = scan_unverified_claims(
            "I've committed the changes and pushed to origin.",
            execution_tier="consultative",
        )
        self.assertTrue(warnings)

    def test_flags_missing_edit_receipts(self) -> None:
        warnings = scan_unverified_claims(
            "I updated README.md with the new section.",
            execution_tier="executing",
        )
        self.assertTrue(any("edit receipts" in item for item in warnings))

    def test_appends_verification_notice(self) -> None:
        content, warnings = verify_lane_b_reply(
            "I've saved your bio to notes.txt.",
            execution_tier="consultative",
        )
        self.assertTrue(warnings)
        self.assertIn("Verification notice", content)


class RouterFallbackTests(unittest.TestCase):
    def test_fallback_reply_does_not_leak_internal_prompt(self) -> None:
        reply = _fallback_reply(
            composer_mode="agent",
            user_prompt="do something",
            context_block="Workspace: workspace_axon_watch",
            reason="Cursor auth probe timed out",
        )
        self.assertNotIn("Workspace context:", reply)
        self.assertNotIn("Operator request:", reply)


if __name__ == "__main__":
    unittest.main()
