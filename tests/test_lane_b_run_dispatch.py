"""Tests for Lane B agent run resolution (G3.8)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.lane_b_run_dispatch import resolve_lane_b_agent_run  # noqa: E402
from app.chat.lane_b_plan_run import finalize_lane_b_plan_run  # noqa: E402
from app.chat.lane_b_stream_execute import LaneBStreamJob, execute_lane_b_stream  # noqa: E402
from app.persistence import chat_store, run_store  # noqa: E402
from app.runs.service import approve_run, create_run, get_run, stop_run  # noqa: E402
from tests.support.control_plane_db import isolate_control_plane_db  # noqa: E402


class LaneBRunDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        chat_store.reset_store()
        self.addCleanup(chat_store.reset_store)

    def test_full_access_run_executes_immediately_without_approval(self) -> None:
        # Consent in the Agent Dock is the approval; no run-level boundary.
        record = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Implement the toggle",
            linked_run_id=None,
            execution_access="full",
        )
        self.assertEqual("executing", record["phase"])
        self.assertFalse(record["can_approve"])

    def test_consultative_agent_run_enters_executing_without_approval(self) -> None:
        record = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Suggest next steps",
            linked_run_id=None,
            execution_access="consultative",
        )
        self.assertEqual("executing", record["phase"])

    def test_plan_run_is_linked_and_becomes_review_ready(self) -> None:
        created = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Plan the resume behavior",
            linked_run_id=None,
            execution_access="consultative",
            composer_mode="plan",
        )
        self.assertEqual("plan", created["mode"])
        self.assertEqual("executing", created["phase"])
        self.assertFalse(created["can_approve"])

        dispatched, reviewed = finalize_lane_b_plan_run(
            run_id=str(created["run_id"]),
            lane_b_result={
                "dispatched": True,
                "runtime_label": "Cursor CLI",
            },
            reply_text="Plan ready.\n\nConfidence: 8/10",
        )
        self.assertTrue(dispatched)
        self.assertIsNotNone(reviewed)
        self.assertEqual("review_ready", reviewed["phase"])

        resumed = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Revise the verification step",
            linked_run_id=str(created["run_id"]),
            execution_access="consultative",
            composer_mode="plan",
        )
        self.assertEqual(str(created["run_id"]), str(resumed["run_id"]))
        self.assertEqual("executing", resumed["phase"])

    def test_streamed_plan_run_finalizes_to_review_ready(self) -> None:
        """Streaming Plan jobs must leave the linked run at review_ready (not stuck executing)."""
        created = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Plan the July fee reconciliation",
            linked_run_id=None,
            execution_access="consultative",
            composer_mode="plan",
        )
        thread = chat_store.create_thread(
            workspace_id="workspace_alpha",
            run_id=str(created["run_id"]),
            created_at="2026-07-23T04:26:39Z",
            thread_kind="ide",
        )
        agent_message = chat_store.save_message(
            {
                "message_id": "message_agent_plan_stream",
                "thread_id": thread["thread_id"],
                "workspace_id": "workspace_alpha",
                "run_id": created["run_id"],
                "role": "agent",
                "content": "",
                "created_at": "2026-07-23T04:26:39Z",
            }
        )
        system_message = chat_store.save_message(
            {
                "message_id": "message_system_plan_stream",
                "thread_id": thread["thread_id"],
                "workspace_id": "workspace_alpha",
                "run_id": created["run_id"],
                "role": "system",
                "content": "Lane B (plan) — generating reply…",
                "created_at": "2026-07-23T04:26:39Z",
            }
        )
        plan_body = (
            "# July fee plan\n\n"
            "## Goal\n\nReconcile July payments.\n\n"
            "## Locked decisions\n\nUse Young Eagles roster.\n\n"
            "1. Parse the bank CSV\n"
            "2. Match learners\n"
            "3. Export Paid / Not Paid\n\n"
            "## Out of scope\n\nReminders.\n\n"
            "## Sources\n\n- scripts/july-fee-bank-reconciliation-report.ts\n\n"
            "## Verification checklist\n\n"
            "- [ ] CSV covers full July\n"
            "- [ ] Every learner appears once\n"
            "- [ ] No reminders sent\n\n"
            "Confidence: 8/10"
        )
        job = LaneBStreamJob(
            thread_id=str(thread["thread_id"]),
            agent_message_id=str(agent_message["message_id"]),
            system_message_id=str(system_message["message_id"]),
            workspace_id="workspace_alpha",
            content="Plan the July fee reconciliation",
            composer_mode="plan",
            active_file_path=None,
            editor_selection=None,
            terminal_snippet=None,
            image_paths=(),
            runtime_target=None,
            runtime_model=None,
            execution_access="consultative",
            dispatch_run_id=str(created["run_id"]),
            created_at="2026-07-23T04:26:39Z",
        )
        with patch(
            "app.chat.lane_b_stream_execute.generate_lane_b_result",
            return_value={
                "content": plan_body,
                "dispatched": True,
                "runtime_id": "cursor_local",
                "runtime_label": "Cursor CLI",
                "reason": "",
            },
        ), patch(
            "app.chat.lane_b_stream_execute.resolve_workspace_root",
            return_value=Path("/tmp/unused-workspace"),
        ), patch(
            "app.chat.lane_b_stream_execute.verify_lane_b_reply",
            side_effect=lambda content, **_kwargs: (content, []),
        ), patch(
            "app.chat.lane_b_stream_execute.maybe_attach_plan_artifact",
            side_effect=lambda **kwargs: (kwargs["agent_content"], None),
        ), patch(
            "app.chat.lane_b_stream_execute.publish_completion_milestone",
        ), patch(
            "app.chat.lane_b_stream_execute.publish_chat_stream_event",
        ), patch(
            "app.chat.lane_b_stream_execute.close_chat_stream",
        ), patch(
            "app.chat.lane_b_stream_execute.clear_chat_stream_buffer",
        ), patch(
            "app.chat.lane_b_stream_execute.bind_agent_generated_images",
            return_value=[],
        ), patch(
            "app.chat.lane_b_stream_execute.lane_b_open_file_ui_action",
            return_value=None,
        ):
            execute_lane_b_stream(job)

        finalized = get_run(str(created["run_id"]))
        self.assertEqual("review_ready", finalized["phase"])
        messages = chat_store.list_thread_messages(str(thread["thread_id"]))
        updated_system = next(
            (row for row in messages if row["message_id"] == system_message["message_id"]),
            None,
        )
        self.assertIsNotNone(updated_system)
        assert updated_system is not None
        self.assertIn("review_ready", str(updated_system.get("content") or ""))

    def test_reuses_executing_run_for_follow_up_turn(self) -> None:
        created = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="First turn",
            linked_run_id=None,
            execution_access="full",
        )
        self.assertEqual("executing", created["phase"])

        reused = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Second turn",
            linked_run_id=str(created["run_id"]),
            execution_access="full",
        )
        self.assertEqual(str(created["run_id"]), str(reused["run_id"]))

    def test_full_access_auto_approves_legacy_awaiting_approval_run(self) -> None:
        legacy = create_run(
            workspace_id="workspace_alpha",
            mode="agent",
            summary="Legacy boundary run",
            requires_approval=True,
        )
        self.assertEqual("awaiting_approval", legacy["phase"])

        resolved = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Follow-up",
            linked_run_id=str(legacy["run_id"]),
            execution_access="full",
        )
        self.assertEqual(str(legacy["run_id"]), str(resolved["run_id"]))
        self.assertEqual("executing", resolved["phase"])

    def test_full_access_resumes_review_ready_linked_run(self) -> None:
        created = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="First turn",
            linked_run_id=None,
            execution_access="full",
        )
        from app.runs.service import mark_review_ready  # noqa: WPS433

        review_ready = mark_review_ready(str(created["run_id"]))
        self.assertEqual("review_ready", review_ready["phase"])

        resumed = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Follow-up after review",
            linked_run_id=str(created["run_id"]),
            execution_access="full",
        )
        self.assertEqual(str(created["run_id"]), str(resumed["run_id"]))
        self.assertEqual("executing", resumed["phase"])

    def test_full_access_resumes_paused_linked_run(self) -> None:
        created = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="First turn",
            linked_run_id=None,
            execution_access="full",
        )
        paused = stop_run(str(created["run_id"]))
        self.assertEqual("paused", paused["phase"])

        resumed = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Continue after stop",
            linked_run_id=str(created["run_id"]),
            execution_access="full",
        )
        self.assertEqual(str(created["run_id"]), str(resumed["run_id"]))
        self.assertEqual("executing", resumed["phase"])

    def test_consultative_resumes_review_ready_linked_run(self) -> None:
        created = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="First turn",
            linked_run_id=None,
            execution_access="consultative",
        )
        from app.runs.service import mark_review_ready  # noqa: WPS433

        review_ready = mark_review_ready(str(created["run_id"]))
        self.assertEqual("review_ready", review_ready["phase"])

        resumed = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Follow-up after review",
            linked_run_id=str(created["run_id"]),
            execution_access="consultative",
        )
        self.assertEqual(str(created["run_id"]), str(resumed["run_id"]))
        self.assertEqual("executing", resumed["phase"])

    def test_consultative_resumes_paused_linked_run(self) -> None:
        created = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="First turn",
            linked_run_id=None,
            execution_access="consultative",
        )
        paused = stop_run(str(created["run_id"]))
        self.assertEqual("paused", paused["phase"])

        resumed = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Continue after stop",
            linked_run_id=str(created["run_id"]),
            execution_access="consultative",
        )
        self.assertEqual(str(created["run_id"]), str(resumed["run_id"]))
        self.assertEqual("executing", resumed["phase"])


if __name__ == "__main__":
    unittest.main()
