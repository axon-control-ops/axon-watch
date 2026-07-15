from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.reply_verification import (  # noqa: E402
    scan_unverified_claims,
    verify_edit_paths,
    verify_lane_b_reply,
)
from app.cli_runtime.router import _fallback_reply  # noqa: E402
from app.cli_runtime.stream_blocks.terminal_blocks import _relative_path  # noqa: E402


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

    def test_git_commit_receipt_clears_consultative_claim(self) -> None:
        content = (
            "Committed successfully with message: Slice 1 — Right dock\n\n"
            ":::terminal git commit -m \"Slice 1 — Right dock\"\n"
            "[main abc1234] Slice 1 — Right dock\n"
            ":::"
        )
        warnings = scan_unverified_claims(content, execution_tier="consultative")
        self.assertFalse(
            any("past-tense execution claims" in item for item in warnings),
            warnings,
        )
        verified, verified_warnings = verify_lane_b_reply(
            content,
            execution_tier="executing",
        )
        self.assertNotIn("Verification notice", verified)
        self.assertEqual(verified_warnings, [])


class OutsideWorkspaceEditVerificationTests(unittest.TestCase):
    def test_relative_path_keeps_absolute_when_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as outside:
            workspace_root = Path(workspace)
            outside_file = Path(outside) / "Annatjie_Makunyane_Unit_13855_Submission_Only.html"
            outside_file.write_text("<html></html>", encoding="utf-8")

            rendered = _relative_path(str(outside_file), str(workspace_root))
            self.assertEqual(rendered, outside_file.resolve().as_posix())
            self.assertNotEqual(rendered, outside_file.name)

    def test_verify_edit_paths_accepts_absolute_out_of_workspace_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as outside:
            workspace_root = Path(workspace)
            outside_file = Path(outside) / "annatjie-makunyane-cover-page_print.html"
            outside_file.write_text("<html>cover</html>", encoding="utf-8")
            started = time.time() - 5

            warnings = verify_edit_paths(
                workspace_root,
                [outside_file.resolve().as_posix()],
                run_started_epoch=started,
            )
            self.assertEqual(warnings, [])

    def test_basename_only_outside_workspace_still_missing_under_active_root(self) -> None:
        """Legacy basename receipts remain strict — absolute receipts are the fix."""
        with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as outside:
            workspace_root = Path(workspace)
            outside_file = Path(outside) / "Annatjie_Makunyane_Unit_13855_Final_Submission.html"
            outside_file.write_text("<html>final</html>", encoding="utf-8")

            warnings = verify_edit_paths(
                workspace_root,
                [outside_file.name],
                run_started_epoch=time.time() - 5,
            )
            self.assertTrue(any("missing on disk" in item for item in warnings))

    def test_verify_lane_b_reply_does_not_flag_absolute_outside_edits(self) -> None:
        with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as outside:
            workspace_root = Path(workspace)
            outside_file = Path(outside) / "Annatjie_Makunyane_Unit_13855_Final_Submission.html"
            outside_file.write_text("<html>final</html>", encoding="utf-8")
            abs_path = outside_file.resolve().as_posix()
            content = (
                f"I've updated the submission pack.\n\n"
                f":::edit {abs_path} +12 -3\n"
                f"- old\n+ new\n"
                f":::\n"
            )
            verified, warnings = verify_lane_b_reply(
                content,
                execution_tier="executing",
                workspace_root=workspace_root,
                run_started_epoch=time.time() - 5,
            )
            self.assertEqual(warnings, [])
            self.assertNotIn("Verification notice", verified)


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
