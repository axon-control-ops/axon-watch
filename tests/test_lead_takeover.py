"""Continuous Lead takeover after specialist completions."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_app_loader import prepare_control_plane_imports
from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


class LeadTakeoverTests(unittest.TestCase):
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

    def test_extract_lead_next(self) -> None:
        from app.workspace_agents.lead_takeover import extract_lead_next

        text = (
            "Verified tests.\n"
            "Blockers / Lead next:\n"
            "- Lead: decide when to run the parent notify campaign once storage is live.\n"
            "Confidence: 9/10"
        )
        self.assertIn("decide when to run the parent notify", extract_lead_next(text))

    def test_ad_hoc_specialist_completion_posts_dana_takeover(self) -> None:
        from app.persistence import chat_store, task_store
        from app.workspace_agents.lead_replan import notify_lead_after_worker_task

        reply = (
            "Built parent graduation survey card.\n"
            "Blockers / Lead next: Lead: decide notify campaign once storage is live.\n"
            "Confidence: 9/10"
        )
        with patch("app.live_events.broadcast_material_change"):
            result = notify_lead_after_worker_task(
                workspace_id="workspace_dashpro",
                task_id="",
                run_id="run_priya_grad_1",
                employee_role="frontend",
                employee_name="Priya",
                phase="completed",
                reply_text=reply,
            )
        self.assertEqual("ok_ad_hoc", result.get("status"))
        takeover = result.get("takeover") or {}
        self.assertEqual("posted", takeover.get("status"))
        self.assertTrue(takeover.get("follow_up_task_id"))

        thread_id = takeover.get("thread_id")
        self.assertTrue(thread_id)
        messages = chat_store.list_thread_messages(str(thread_id))
        agent_msgs = [m for m in messages if m.get("role") == "agent"]
        self.assertTrue(any("Lead takeover" in str(m.get("content") or "") for m in agent_msgs))
        self.assertTrue(
            any("Priya" in str(m.get("content") or "") for m in agent_msgs)
        )

        follow = task_store.get_task(str(takeover.get("follow_up_task_id")))
        assert follow is not None
        self.assertEqual("lead", follow.get("owner_role"))
        self.assertIn("Lead follow-up", follow.get("goal") or "")

        # Idempotent for the same run.
        with patch("app.live_events.broadcast_material_change"):
            again = notify_lead_after_worker_task(
                workspace_id="workspace_dashpro",
                task_id="",
                run_id="run_priya_grad_1",
                employee_role="frontend",
                employee_name="Priya",
                phase="completed",
                reply_text=reply,
            )
        self.assertEqual("already_posted", (again.get("takeover") or {}).get("status"))


if __name__ == "__main__":
    unittest.main()
