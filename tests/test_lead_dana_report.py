"""Specialists report to Dana; Lead posts a detailed IDE rollup after synthesis."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_app_loader import prepare_control_plane_imports
from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


class LeadDanaReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = prepare_control_plane_imports()
        self.addCleanup(self._restore)
        from app.persistence import chat_store, run_store, task_store
        from app.workspace_agents import lead_plan_store

        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        lead_plan_store.reset_store()
        chat_store.reset_store()

    def _restore(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.modules.update(self._saved)

    def test_synthesis_posts_dana_ide_rollup_and_specialist_status(self) -> None:
        from app.persistence import chat_store, task_store
        from app.workspace_agents import lead_plan_store
        from app.workspace_agents.lead_dana_report import (
            DANA_SYNTHESIS_RECEIPT_KIND,
            SPECIALIST_STATUS_RECEIPT_KIND,
        )
        from app.workspace_agents.lead_fan_out import materialize_lead_fan_out
        from app.workspace_agents.lead_replan import (
            notify_lead_after_worker_task,
            synthesize_lead_plan,
        )
        from app.workspace_agents.lead_vaxon_handoff import HANDOFF_RECEIPT_KIND

        with patch("app.live_events.broadcast_material_change"):
            result = materialize_lead_fan_out(
                workspace_id="workspace_axon_watch",
                goal="Check with all teammates for a release recommendation",
                mode="fan_out",
                create_runs=False,
            )
            plan_id = result["plan_id"]
            tasks = result["tasks"]
            self.assertGreaterEqual(len(tasks), 2)

            # Leave one task open — notify should report to Dana but not synthesize yet.
            first = tasks[0]
            leased = task_store.lease_task(
                str(first["task_id"]),
                lease_holder=f"test-{first['owner_role']}",
            )
            task_store.complete_task(
                str(leased["task_id"]),
                terminal_outcome=f"{first['owner_role']} done",
            )
            partial = notify_lead_after_worker_task(
                workspace_id="workspace_axon_watch",
                task_id=str(leased["task_id"]),
                run_id="run_partial_1",
                employee_role=str(first["owner_role"]),
                employee_name=str(first.get("assignee_name") or first["owner_role"]),
                phase="completed",
                reply_text="Partial specialist receipt for Lead.",
            )
            self.assertEqual("ok", partial.get("status"))
            self.assertEqual("awaiting_results", (partial.get("synthesis") or {}).get("status"))
            self.assertIn((partial.get("takeover") or {}).get("status"), {"posted", "already_posted"})

            last_synthesis = None
            for task in tasks[1:]:
                leased = task_store.lease_task(
                    str(task["task_id"]),
                    lease_holder=f"test-{task['owner_role']}",
                )
                task_store.complete_task(
                    str(leased["task_id"]),
                    terminal_outcome=f"{task['owner_role']} approved",
                )
                notified = notify_lead_after_worker_task(
                    workspace_id="workspace_axon_watch",
                    task_id=str(leased["task_id"]),
                    run_id=f"run_{task['owner_role']}",
                    employee_role=str(task["owner_role"]),
                    employee_name=str(task.get("assignee_name") or task["owner_role"]),
                    phase="completed",
                    reply_text=f"{task['owner_role']} full report with Confidence: 8/10",
                )
                last_synthesis = notified.get("synthesis")

            # Final specialist should have auto-synthesized.
            self.assertIsNotNone(last_synthesis)
            assert last_synthesis is not None
            self.assertIn(last_synthesis.get("status"), {"completed", "awaiting_engagement"})
            completed = synthesize_lead_plan(plan_id)

        self.assertIn(completed["status"], {"completed", "awaiting_engagement"})
        self.assertIn((completed.get("vaxon_handoff") or {}).get("status"), {"posted", "already_posted"})
        self.assertIn((completed.get("dana_handoff") or {}).get("status"), {"posted", "already_posted"})

        kinds = {row["kind"] for row in lead_plan_store.list_receipts(plan_id)}
        self.assertIn("lead_synthesis_completed", kinds)
        self.assertIn(HANDOFF_RECEIPT_KIND, kinds)
        self.assertIn(DANA_SYNTHESIS_RECEIPT_KIND, kinds)
        self.assertIn(SPECIALIST_STATUS_RECEIPT_KIND, kinds)

        dana_thread_id = (completed.get("dana_handoff") or {}).get("thread_id")
        self.assertTrue(dana_thread_id)
        messages = chat_store.list_thread_messages(str(dana_thread_id))
        agent_bodies = [
            str(message.get("content") or "")
            for message in messages
            if str(message.get("role") or "") == "agent"
        ]
        self.assertTrue(any("Dana here — Lead team rollup" in body for body in agent_bodies))
        self.assertTrue(any("reported in — shift completed" in body for body in agent_bodies))
        self.assertTrue(any("Next best steps" in body for body in agent_bodies))


class DynamicNextBestStepsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = prepare_control_plane_imports()
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.modules.update(self._saved)

    def test_surfaces_failed_specialists_by_name(self) -> None:
        from app.workspace_agents.lead_dana_report import _dynamic_next_best_steps

        findings = [
            {"assignee_name": "Lila", "owner_role": "frontend", "status": "failed"},
            {"assignee_name": "Cole", "owner_role": "backend", "status": "completed"},
        ]
        steps = _dynamic_next_best_steps(findings)
        self.assertTrue(any("Lila" in step and "failed" in step for step in steps))

    def test_surfaces_real_decision_gate_from_excerpt(self) -> None:
        from app.workspace_agents.lead_dana_report import _dynamic_next_best_steps

        findings = [
            {
                "assignee_name": "Dana",
                "owner_role": "frontend",
                "status": "completed",
                "specialist_reply_excerpt": (
                    "Confirm the DashPro chat-ingest handoff before I ship it live."
                ),
            },
        ]
        steps = _dynamic_next_best_steps(findings)
        self.assertTrue(any(step.startswith("Confirm (Dana):") for step in steps))

    def test_falls_back_to_generic_step_when_nothing_concrete(self) -> None:
        from app.workspace_agents.lead_dana_report import _dynamic_next_best_steps

        findings = [
            {"assignee_name": "Cole", "owner_role": "backend", "status": "completed"},
        ]
        steps = _dynamic_next_best_steps(findings)
        self.assertTrue(any("dig into" in step.lower() for step in steps))


if __name__ == "__main__":
    unittest.main()
