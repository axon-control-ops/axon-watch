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

        kinds = {row["kind"] for row in lead_plan_store.list_receipts(result["plan_id"])}
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

        # Idempotent second synthesis/handoff path
        again = synthesize_lead_plan(result["plan_id"])
        self.assertEqual("already_posted", (again.get("vaxon_handoff") or {}).get("status"))


if __name__ == "__main__":
    unittest.main()
