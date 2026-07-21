"""Unit tests for durable plan file store and capture service."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.plans.file_store import PlanStoreError, plan_file_path, read_plan_file  # noqa: E402
from app.plans.service import (  # noqa: E402
    PlanCaptureError,
    build_plan_transcript_fence,
    capture_plan_from_reply,
    extract_plan_title,
    is_durable_plan_body,
    maybe_attach_plan_artifact,
    strip_leading_process_narration,
    strip_noisy_fences,
)

COMPLETE_PLAN = """# Mobile remote first, then employee upgrades

## Goal
Ship phone remote control, then harden agent coordination.

## Steps
1. Stabilize OperatorMobileShell tunnel + compact cockpit
2. Add push/status receipts for remote runs
3. Wire independent threads + watcher→lead escalation
4. Verify Day-1 dry-run attestation path

## Verification
- Open plan from View Plan and confirm structured body
- Smoke tunnel + mobile shell on a real device session
"""

NARRATION_REPLY = """# I'll look through the repo for the mobile control plan and any numbered options that "3" might refer to.

I'll look through the repo for the mobile control plan and any numbered options that "3" might refer to.

The request is just "3" — I'll check the planning docs and recent thread for what that number maps to.

Choice **3** = both, phased: mobile remote first, then employee upgrades. Gathering the gaps and current shell so I can draft that plan.

I have enough: **3** means mobile remote first, then the highest-value employee upgrades. Drafting that phased plan now.
"""

CLARIFYING_REPLY = """# I'll search the repo for mobile control

I've mapped the pasted gaps to real code. One choice changes the whole plan before I write it.

*What should this plan focus on?**

1.*Employee / coordination gaps* — independent threads
2.*Mobile remote control* — phone shell
3.*Both, phased* — mobile remote first

Reply with `1`, `2`, or `3`.
"""


class PlanStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.root_patch = patch(
            "app.plans.file_store.resolve_workspace_root",
            return_value=self.root,
        )
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def test_extract_title_from_heading(self) -> None:
        self.assertEqual(
            "Tunnel cutover",
            extract_plan_title("# Tunnel cutover\n\n1. Disable systemd\n"),
        )

    def test_extract_title_skips_process_openers(self) -> None:
        self.assertEqual("Untitled plan", extract_plan_title(NARRATION_REPLY))

    def test_strip_tool_and_thinking_fences(self) -> None:
        raw = (
            ":::thinking\nlooking around\n:::\n\n"
            ":::tool Createplan\n\n"
            "# Soft cutover\n\n1. Proxy :7734\n"
        )
        cleaned = strip_noisy_fences(raw)
        self.assertIn("# Soft cutover", cleaned)
        self.assertNotIn("Createplan", cleaned)
        self.assertNotIn("thinking", cleaned)

    def test_rejects_narration_and_clarifying_replies(self) -> None:
        self.assertFalse(is_durable_plan_body(NARRATION_REPLY))
        self.assertFalse(is_durable_plan_body(CLARIFYING_REPLY))
        self.assertTrue(is_durable_plan_body(COMPLETE_PLAN))
        with self.assertRaises(PlanCaptureError):
            capture_plan_from_reply(
                workspace_id="workspace_alpha",
                thread_id="thread_1",
                source_message_id="message_agent_bad",
                content=NARRATION_REPLY,
            )

    def test_capture_writes_markdown_and_fence(self) -> None:
        record, fence = capture_plan_from_reply(
            workspace_id="workspace_alpha",
            thread_id="thread_1",
            source_message_id="message_agent_1",
            content=COMPLETE_PLAN,
        )
        self.assertTrue(record.plan_id.startswith("plan_"))
        self.assertEqual("Mobile remote first, then employee upgrades", record.title)
        path = Path(record.path)
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("plan_id:", text)
        self.assertIn("# Mobile remote first, then employee upgrades", text)
        self.assertEqual(fence, build_plan_transcript_fence(record.plan_id, record.title))
        loaded = read_plan_file("workspace_alpha", record.plan_id)
        self.assertEqual(record.title, loaded.title)
        self.assertIn("Stabilize OperatorMobileShell", loaded.content)

    def test_rejects_invalid_plan_id(self) -> None:
        with self.assertRaises(PlanStoreError):
            plan_file_path("workspace_alpha", "../evil")

    def test_maybe_attach_only_for_plan_mode(self) -> None:
        content, meta = maybe_attach_plan_artifact(
            composer_mode="agent",
            workspace_id="workspace_alpha",
            thread_id="thread_1",
            source_message_id="message_agent_1",
            agent_content=COMPLETE_PLAN,
        )
        self.assertIsNone(meta)
        self.assertEqual(COMPLETE_PLAN, content)

        content, meta = maybe_attach_plan_artifact(
            composer_mode="plan",
            workspace_id="workspace_alpha",
            thread_id="thread_1",
            source_message_id="message_agent_2",
            agent_content=COMPLETE_PLAN,
        )
        self.assertIsNotNone(meta)
        assert meta is not None
        self.assertIn(":::plan ", content)
        self.assertEqual(meta["title"], "Mobile remote first, then employee upgrades")

    def test_maybe_attach_skips_incomplete_plan_mode_replies(self) -> None:
        content, meta = maybe_attach_plan_artifact(
            composer_mode="plan",
            workspace_id="workspace_alpha",
            thread_id="thread_1",
            source_message_id="message_agent_3",
            agent_content=NARRATION_REPLY,
        )
        self.assertIsNone(meta)
        self.assertNotIn(":::plan ", content)
        self.assertEqual(NARRATION_REPLY, content)

    def test_strip_noisy_fences_drops_research_and_thinking(self) -> None:
        polluted = (
            "# Centre brief\n\n"
            "I'll review the docs first.\n\n"
            ":::thinking\nDrafting now.\n:::\n\n"
            ":::research Web search\n@kind search\n:::\n\n"
            "## Goal\n"
            "Open an aftercare centre safely.\n\n"
            "## Steps\n"
            "1. Confirm ages and hours\n"
            "2. Set staffing ratios\n"
            "3. Phase the go-live\n\n"
            "## Verification\n"
            "- [ ] Ages documented\n"
            "- [ ] Hours documented\n"
            "- [ ] Ratios documented\n"
        )
        cleaned = strip_leading_process_narration(strip_noisy_fences(polluted))
        self.assertNotIn(":::research", cleaned)
        self.assertNotIn(":::thinking", cleaned)
        self.assertNotIn("I'll review", cleaned)
        self.assertIn("## Goal", cleaned)
        self.assertTrue(is_durable_plan_body(polluted))
        record, _fence = capture_plan_from_reply(
            workspace_id="workspace_alpha",
            thread_id="thread_1",
            source_message_id="message_agent_4",
            content=polluted,
        )
        self.assertNotIn(":::research", record.content)
        self.assertNotIn("I'll review", record.content)
        self.assertEqual(
            "Centre brief",
            extract_plan_title(record.content),
        )

    def test_capture_cleans_researched_plan_progress_and_duplicate_title(self) -> None:
        polluted = (
            "# School plan\n\n"
            "Axon research is ready. Next I'll pull local pricing benchmarks.\n\n"
            "# School plan\n\n"
            "## Goal\n"
            "Open an aftercare centre safely with evidence-backed fees.\n\n"
            "## Steps\n"
            "1. Confirm local prices\n"
            "2. Set staffing ratios\n"
            "3. Publish parent materials\n\n"
            "## Verification\n"
            "- [ ] Prices cited\n"
            "- [ ] Ratios documented\n"
            "- [ ] Materials reviewed\n"
        )
        record, _fence = capture_plan_from_reply(
            workspace_id="workspace_alpha",
            thread_id="thread_1",
            source_message_id="message_agent_5",
            content=polluted,
        )
        self.assertEqual(1, record.content.count("# School plan"))
        self.assertNotIn("Axon research is ready", record.content)
        self.assertTrue(record.content.startswith("# School plan\n\n## Goal"))


if __name__ == "__main__":
    unittest.main()
