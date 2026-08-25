"""A cross-workspace handoff must tell the source Lead how it ended.

Regression guard for a real gap: creating a handoff posted one ack to the
source workspace ("routed to Target Lead") and then went completely silent.
Nothing ever told the source Lead whether the target workspace's delegated
task actually finished or failed -- the whole point of Lead-to-Lead handoff
was a one-way ticket, not a conversation with an answer.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import chat_store, handoff_store, task_store  # noqa: E402
from app.workspace_handoff_routing import notify_completed_handoffs  # noqa: E402


class HandoffCompletionNoticeTests(unittest.TestCase):
    def setUp(self) -> None:
        handoff_store.reset_store()
        self.addCleanup(handoff_store.reset_store)

    def _routed_handoff(self, *, source: str, target: str, task_status: str) -> tuple[str, str]:
        task = task_store.create_task(
            workspace_id=target,
            goal="Fix parent link request UI bug",
            acceptance_criteria="Bug reproduced and fixed",
            risk="normal",
            owner_role="frontend",
        )
        task_id = str(task["task_id"])
        if task_status == "completed":
            task_store.complete_task(task_id, terminal_outcome="fixed and verified")
        elif task_status == "failed":
            task_store.fail_task(task_id, terminal_outcome="blocked on missing test fixture")
        elif task_status == "cancelled":
            task_store.cancel_task(task_id, terminal_outcome="superseded by newer request")

        handoff = handoff_store.create_handoff_record(
            source_workspace_id=source,
            target_workspace_id=target,
            task="Fix parent link request UI bug",
            reason="TPS reported it during standup",
        )
        handoff_store.update_handoff(
            handoff["handoff_id"],
            status="routed",
            target_task_id=task_id,
            routed_role="frontend",
        )
        return handoff["handoff_id"], task_id

    def test_completed_handoff_notifies_the_source_lead(self) -> None:
        handoff_id, _task_id = self._routed_handoff(
            source="workspace_smoke", target="workspace_alpha", task_status="completed"
        )
        closed = notify_completed_handoffs()
        self.assertEqual(1, len(closed))
        self.assertEqual("completed", closed[0]["outcome"])

        handoff = handoff_store.get_handoff(handoff_id)
        assert handoff is not None
        self.assertEqual("completed", handoff["status"])

    def test_failed_handoff_notifies_with_the_failure_outcome(self) -> None:
        handoff_id, _task_id = self._routed_handoff(
            source="workspace_smoke", target="workspace_alpha", task_status="failed"
        )
        closed = notify_completed_handoffs()
        self.assertEqual(1, len(closed))
        self.assertEqual("failed", closed[0]["outcome"])
        handoff = handoff_store.get_handoff(handoff_id)
        assert handoff is not None
        self.assertEqual("failed", handoff["status"])

    def test_still_open_target_task_is_not_notified_yet(self) -> None:
        # An 'open' or 'leased' task means the work is still in flight -- the
        # whole point is to wait for a real terminal outcome before speaking.
        self._routed_handoff(source="workspace_smoke", target="workspace_alpha", task_status="open")
        closed = notify_completed_handoffs()
        self.assertEqual([], closed)

    def test_a_handoff_is_never_notified_twice(self) -> None:
        self._routed_handoff(
            source="workspace_smoke", target="workspace_alpha", task_status="completed"
        )
        first = notify_completed_handoffs()
        second = notify_completed_handoffs()
        self.assertEqual(1, len(first))
        self.assertEqual([], second)

    def test_notice_lands_in_the_source_lead_thread_with_the_outcome(self) -> None:
        from app.workspace_agents import build_company_roster

        self._routed_handoff(
            source="workspace_smoke", target="workspace_alpha", task_status="completed"
        )
        notify_completed_handoffs()

        roster = build_company_roster("workspace_smoke")
        lead = next(
            row for row in roster.get("employees") or [] if str(row.get("role")).lower() == "lead"
        )
        thread = chat_store.find_thread_for_employee(
            "workspace_smoke", employee_id=str(lead["employee_id"]), thread_kind="ide"
        )
        self.assertIsNotNone(thread)
        assert thread is not None
        messages = chat_store.list_thread_messages(str(thread["thread_id"]))
        bodies = [str(m.get("content") or "") for m in messages]
        self.assertTrue(
            any("completed" in body.lower() for body in bodies),
            f"expected a completion message in the source Lead thread, got: {bodies}",
        )


if __name__ == "__main__":
    unittest.main()
