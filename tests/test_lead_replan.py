"""Gate 5 — persistent conflicts, receipt-backed replans, synthesis."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_app_loader import prepare_control_plane_imports
from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


class LeadReplanTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = prepare_control_plane_imports()
        self.addCleanup(self._restore)
        from app.persistence import run_store, task_store
        from app.workspace_agents import lead_plan_store

        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        lead_plan_store.reset_store()

    def _restore(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.modules.update(self._saved)

    def test_leased_paths_block_overlapping_task_from_another_plan(self) -> None:
        from app.persistence import task_store

        first = task_store.create_task(
            workspace_id="workspace_axon_watch",
            goal="Edit console shell",
            owner_role="frontend",
            exclusive_paths=["apps/console-web/src"],
        )
        second = task_store.create_task(
            workspace_id="workspace_axon_watch",
            goal="Edit shell store",
            owner_role="backend",
            exclusive_paths=["apps/console-web/src/stores/shell.ts"],
        )
        task_store.lease_task(first["task_id"], lease_holder="lead-frontend")
        with self.assertRaises(task_store.TaskLedgerError) as ctx:
            task_store.lease_task(second["task_id"], lease_holder="lead-backend")
        self.assertIn("exclusive path conflict", str(ctx.exception))

    def test_replan_cancels_obsolete_tasks_and_persists_receipts(self) -> None:
        from app.persistence import task_store
        from app.workspace_agents import lead_plan_store
        from app.workspace_agents.lead_fan_out import materialize_lead_fan_out
        from app.workspace_agents.lead_replan import replan_lead_goal

        first = materialize_lead_fan_out(
            workspace_id="workspace_axon_watch",
            goal="Fix the backend API then update the frontend screen",
            mode="sequential",
            create_runs=False,
        )
        replacement = replan_lead_goal(
            workspace_id="workspace_axon_watch",
            goal="Check with all teammates on the revised safe approach",
            mode="fan_out",
            create_runs=False,
        )
        self.assertEqual(first["plan_id"], replacement["replan"]["supersedes_plan_id"])
        self.assertTrue(replacement["replan"]["cancelled_task_ids"])
        for task_id in replacement["replan"]["cancelled_task_ids"]:
            task = task_store.get_task(task_id)
            self.assertIsNotNone(task)
            assert task is not None
            self.assertEqual("cancelled", task["status"])
        old_plan = lead_plan_store.get_plan(first["plan_id"])
        self.assertIsNotNone(old_plan)
        assert old_plan is not None
        self.assertEqual("superseded", old_plan["status"])
        old_receipt_kinds = {
            row["kind"] for row in lead_plan_store.list_receipts(first["plan_id"])
        }
        new_receipt_kinds = {
            row["kind"] for row in lead_plan_store.list_receipts(replacement["plan_id"])
        }
        self.assertIn("lead_plan_superseded", old_receipt_kinds)
        self.assertIn("lead_replan_materialized", new_receipt_kinds)

    def test_synthesis_waits_then_records_terminal_findings(self) -> None:
        from app.persistence import task_store
        from app.workspace_agents import lead_plan_store
        from app.workspace_agents.lead_fan_out import materialize_lead_fan_out
        from app.workspace_agents.lead_replan import synthesize_lead_plan

        result = materialize_lead_fan_out(
            workspace_id="workspace_axon_watch",
            goal="Check with all teammates for a release recommendation",
            mode="fan_out",
            create_runs=False,
        )
        waiting = synthesize_lead_plan(result["plan_id"])
        self.assertEqual("awaiting_results", waiting["status"])

        for task in result["tasks"]:
            leased = task_store.lease_task(
                str(task["task_id"]),
                lease_holder=f"test-{task['owner_role']}",
            )
            task_store.complete_task(
                str(leased["task_id"]),
                terminal_outcome=f"{task['owner_role']} approved",
            )

        completed = synthesize_lead_plan(result["plan_id"])
        self.assertEqual("completed", completed["status"])
        self.assertEqual(len(result["tasks"]), len(completed["findings"]))
        self.assertIn("approved", completed["summary"])
        kinds = {
            row["kind"] for row in lead_plan_store.list_receipts(result["plan_id"])
        }
        self.assertIn("lead_synthesis_completed", kinds)

    def test_synthesis_blocks_when_linked_specialist_failed(self) -> None:
        from app.persistence import task_store
        from app.workspace_agents import lead_plan_store
        from app.workspace_agents.lead_fan_out import materialize_lead_fan_out
        from app.workspace_agents.lead_replan import synthesize_lead_plan

        result = materialize_lead_fan_out(
            workspace_id="workspace_axon_watch",
            goal="Fix dashboard UI and assignment idempotency/data cleanup",
            mode="decompose",
            create_runs=False,
        )
        self.assertEqual(["backend", "frontend"], sorted(t["owner_role"] for t in result["tasks"]))

        for task in result["tasks"]:
            leased = task_store.lease_task(
                str(task["task_id"]),
                lease_holder=f"test-{task['owner_role']}",
            )
            if task["owner_role"] == "frontend":
                task_store.complete_task(
                    str(leased["task_id"]),
                    terminal_outcome="frontend diff and validation passed",
                )
            else:
                task_store.cancel_task(
                    str(leased["task_id"]),
                    terminal_outcome="backend validation receipt missing",
                )

        blocked = synthesize_lead_plan(result["plan_id"])

        self.assertEqual("blocked", blocked["status"])
        self.assertEqual(1, len(blocked["blocked_task_ids"]))
        plan = lead_plan_store.get_plan(result["plan_id"])
        assert plan is not None
        self.assertEqual("awaiting_engagement", plan["status"])
        kinds = {
            row["kind"] for row in lead_plan_store.list_receipts(result["plan_id"])
        }
        self.assertIn("lead_synthesis_blocked", kinds)
        self.assertNotIn("lead_synthesis_completed", kinds)

    def test_replan_fails_closed_when_obsolete_run_cannot_stop(self) -> None:
        from app.persistence import task_store
        from app.workspace_agents import lead_plan_store
        from app.workspace_agents.lead_fan_out import materialize_lead_fan_out
        from app.workspace_agents.lead_replan import LeadReplanError, replan_lead_goal

        first = materialize_lead_fan_out(
            workspace_id="workspace_axon_watch",
            goal="Backend API correction",
            mode="sequential",
            create_runs=True,
        )
        with patch(
            "app.workspace_agents.lead_replan.stop_run",
            side_effect=RuntimeError("process registry unavailable"),
        ):
            with self.assertRaises(LeadReplanError):
                replan_lead_goal(
                    workspace_id="workspace_axon_watch",
                    goal="Replacement backend goal",
                    mode="sequential",
                    create_runs=False,
                )

        plan = lead_plan_store.get_plan(first["plan_id"])
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual("active", plan["status"])
        task = task_store.get_task(str(first["tasks"][0]["task_id"]))
        self.assertIsNotNone(task)
        assert task is not None
        self.assertEqual("leased", task["status"])
        kinds = {
            row["kind"] for row in lead_plan_store.list_receipts(first["plan_id"])
        }
        self.assertIn("lead_replan_blocked", kinds)


if __name__ == "__main__":
    unittest.main()
