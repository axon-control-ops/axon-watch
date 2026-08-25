"""Lead synthesis posts one VAXON operator-thread handoff."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_app_loader import prepare_control_plane_imports
from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


class LeadVaxonHandoffTests(unittest.TestCase):
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

    def test_synthesis_posts_vaxon_message_and_marks_awaiting_engagement(self) -> None:
        from app.persistence import chat_store, task_store
        from app.workspace_agents import lead_plan_store
        from app.workspace_agents.lead_fan_out import materialize_lead_fan_out
        from app.workspace_agents.lead_replan import synthesize_lead_plan
        from app.workspace_agents.lead_vaxon_handoff import HANDOFF_RECEIPT_KIND

        with patch("app.live_events.broadcast_material_change") as broadcast:
            result = materialize_lead_fan_out(
                workspace_id="workspace_axon_watch",
                goal="Check with all teammates for a release recommendation",
                mode="fan_out",
                create_runs=False,
            )
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
        handoff = completed.get("vaxon_handoff") or {}
        self.assertEqual("posted", handoff.get("status"))
        self.assertTrue(handoff.get("message_id"))
        broadcast.assert_called()

        plan = lead_plan_store.get_plan(result["plan_id"])
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual("awaiting_engagement", plan["status"])

        kinds = {
            row["kind"] for row in lead_plan_store.list_receipts(result["plan_id"])
        }
        self.assertIn("lead_synthesis_completed", kinds)
        self.assertIn(HANDOFF_RECEIPT_KIND, kinds)

        thread = chat_store.get_latest_thread_for_workspace(
            "workspace_axon_watch",
            thread_kind="operator",
        )
        self.assertIsNotNone(thread)
        assert thread is not None
        messages = chat_store.list_thread_messages(str(thread["thread_id"]))
        agent_messages = [row for row in messages if row["role"] == "agent"]
        self.assertTrue(agent_messages)
        self.assertIn("Lead team rollup", agent_messages[-1]["content"])

        again = synthesize_lead_plan(result["plan_id"])
        self.assertEqual("already_posted", (again.get("vaxon_handoff") or {}).get("status"))

    def test_repeated_identical_shift_flash_is_suppressed_but_change_still_posts(self) -> None:
        from app.persistence import chat_store
        from app.workspace_agents.lead_vaxon_handoff import post_ad_hoc_lead_takeover_to_vaxon

        with patch("app.live_events.broadcast_material_change"):
            first = post_ad_hoc_lead_takeover_to_vaxon(
                workspace_id="workspace_axon_watch",
                run_id="run_shift_one",
                employee_role="lead",
                employee_name="Dana",
                phase="completed",
                lead_next="Monitor CI",
                lead_summary="Nothing new since last check.",
            )
            self.assertEqual("posted", first["status"])

            # Next continuous shift, nothing changed — must not add more noise.
            second = post_ad_hoc_lead_takeover_to_vaxon(
                workspace_id="workspace_axon_watch",
                run_id="run_shift_two",
                employee_role="lead",
                employee_name="Dana",
                phase="completed",
                lead_next="Monitor CI",
                lead_summary="Nothing new since last check.",
            )
            self.assertEqual("skipped_duplicate_flash", second["status"])

            # A genuine change (new blocker) must still post.
            third = post_ad_hoc_lead_takeover_to_vaxon(
                workspace_id="workspace_axon_watch",
                run_id="run_shift_three",
                employee_role="lead",
                employee_name="Dana",
                phase="failed",
                lead_next="Fix Codex auth",
                lead_summary="Codex login expired, dispatch blocked.",
            )
            self.assertEqual("posted", third["status"])

        thread = chat_store.get_latest_thread_for_workspace(
            "workspace_axon_watch",
            thread_kind="operator",
        )
        assert thread is not None
        messages = chat_store.list_thread_messages(str(thread["thread_id"]))
        # Two real flashes (system + agent each) = 4 messages; the duplicate added none.
        self.assertEqual(4, len(messages))

    def test_stale_engagement_without_handoff_is_closed_when_work_is_settled(self) -> None:
        from app.persistence import task_store
        from app.workspace_agents import lead_plan_store
        from app.workspace_agents.lead_fan_out import materialize_lead_fan_out
        from app.workspace_agents.lead_vaxon_handoff import (
            STALE_ENGAGEMENT_CLOSED_RECEIPT_KIND,
            list_awaiting_engagement_plans,
        )

        result = materialize_lead_fan_out(
            workspace_id="workspace_axon_watch",
            goal="Check the completed recovery",
            mode="fan_out",
            create_runs=False,
        )
        for task in result["tasks"]:
            task_store.cancel_task(
                str(task["task_id"]),
                terminal_outcome="superseded by completed recovery",
            )
        lead_plan_store.set_plan_status(result["plan_id"], "awaiting_engagement")

        self.assertEqual(
            list_awaiting_engagement_plans(workspace_id="workspace_axon_watch"),
            [],
        )
        plan = lead_plan_store.get_plan(result["plan_id"])
        assert plan is not None
        self.assertEqual(plan["status"], "completed")
        self.assertIn(
            STALE_ENGAGEMENT_CLOSED_RECEIPT_KIND,
            {row["kind"] for row in lead_plan_store.list_receipts(result["plan_id"])},
        )


if __name__ == "__main__":
    unittest.main()
