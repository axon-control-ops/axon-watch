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
        from app.workspace_agents import lead_adhoc_receipt_store, lead_plan_store

        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        lead_plan_store.reset_store()
        lead_adhoc_receipt_store.reset_store()
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
        from app.workspace_agents import lead_adhoc_receipt_store
        from app.workspace_agents.lead_replan import notify_lead_after_worker_task

        reply = (
            "Built parent graduation survey card.\n"
            "Blockers / Lead next: Lead: decide notify campaign once storage is live.\n"
            "Confidence: 9/10"
        )
        with (
            patch("app.live_events.broadcast_material_change"),
            patch("app.live_events.broadcast_spoken_line", return_value=1),
        ):
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
        vaxon = (takeover.get("vaxon_flash") or {})
        self.assertIn(vaxon.get("status"), {"posted", "already_posted"})
        self.assertTrue(vaxon.get("receipt_id"))
        self.assertTrue(vaxon.get("synthesis_receipt_id") or (vaxon.get("synthesis") or {}).get("receipt_id"))

        synthesis = lead_adhoc_receipt_store.find_receipt_for_run(
            run_id="run_priya_grad_1",
            kind=lead_adhoc_receipt_store.KIND_LEAD_SYNTHESIS,
        )
        self.assertIsNotNone(synthesis)
        assert synthesis is not None
        payload = synthesis.get("payload") or {}
        self.assertEqual("Priya", payload.get("employee_name"))
        self.assertIn("graduation", str(payload.get("lead_summary") or "").lower())
        # Raw specialist dump must not be stored as the Lead summary whole cloth.
        self.assertNotIn("Confidence: 9/10", str(payload.get("lead_summary") or ""))

        operator = chat_store.get_latest_thread_for_workspace(
            "workspace_dashpro",
            thread_kind="operator",
        )
        self.assertIsNotNone(operator)
        op_msgs = chat_store.list_thread_messages(str(operator["thread_id"]))
        self.assertTrue(
            any(
                str(m.get("content") or "").startswith("VAXON:")
                and "run_priya_grad_1" in str(m.get("content") or "")
                and "Lead summary:" in str(m.get("content") or "")
                for m in op_msgs
                if m.get("role") == "agent"
            )
        )

        follow = task_store.get_task(str(takeover.get("follow_up_task_id")))
        assert follow is not None
        self.assertEqual("lead", follow.get("owner_role"))
        self.assertIn("Lead follow-up", follow.get("goal") or "")

        # Idempotent for the same run — takeover stays already_posted; VAXON receipt too.
        with (
            patch("app.live_events.broadcast_material_change"),
            patch("app.live_events.broadcast_spoken_line", return_value=1),
        ):
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
        again_vaxon = (again.get("takeover") or {}).get("vaxon_flash") or {}
        self.assertEqual("already_posted", again_vaxon.get("status"))

    def test_failed_specialist_shift_keeps_lead_follow_up_open(self) -> None:
        from app.persistence import task_store
        from app.workspace_agents.lead_takeover import post_lead_takeover_report

        with (
            patch("app.live_events.broadcast_material_change"),
            patch("app.live_events.broadcast_spoken_line", return_value=1),
        ):
            takeover = post_lead_takeover_report(
                workspace_id="workspace_dashpro",
                run_id="run_priya_failed_1",
                employee_role="frontend",
                employee_name="Priya",
                phase="failed",
                outcome="targeted test failed",
                reply_text=(
                    "Targeted test failed on the legacy fixture.\n"
                    "Blockers / Lead next: Lead: assign the smallest fixture repair.\n"
                    "Confidence: 8/10"
                ),
                create_follow_up_task=True,
            )

        follow = task_store.get_task(str(takeover.get("follow_up_task_id")))
        self.assertIsNotNone(follow)
        assert follow is not None
        self.assertEqual("open", follow.get("status"))
        self.assertEqual("lead", follow.get("owner_role"))

    def test_lead_shift_completion_posts_vaxon_flash(self) -> None:
        from app.persistence import chat_store
        from app.workspace_agents import lead_adhoc_receipt_store
        from app.workspace_agents.lead_replan import notify_lead_after_worker_task

        reply = (
            "Retried my failed continuous Lead shift. Public site is up; remote CI "
            "is still red until the local contract fix lands.\n"
            "Next: On your go-ahead commit/push the contract fix.\n"
            "Confidence: 8/10"
        )
        with (
            patch("app.live_events.broadcast_material_change"),
            patch("app.live_events.broadcast_spoken_line", return_value=1),
        ):
            result = notify_lead_after_worker_task(
                workspace_id="workspace_dashpro",
                task_id="",
                run_id="run_dana_lead_1",
                employee_role="lead",
                employee_name="Dana",
                phase="completed",
                reply_text=reply,
            )
        self.assertEqual("ok_lead_shift", result.get("status"))
        vaxon = result.get("vaxon_flash") or {}
        self.assertIn(vaxon.get("status"), {"posted", "already_posted"})

        synthesis = lead_adhoc_receipt_store.find_receipt_for_run(
            run_id="run_dana_lead_1",
            kind=lead_adhoc_receipt_store.KIND_LEAD_SYNTHESIS,
        )
        self.assertIsNotNone(synthesis)
        assert synthesis is not None
        self.assertEqual("Dana", (synthesis.get("payload") or {}).get("employee_name"))
        self.assertEqual("lead", (synthesis.get("payload") or {}).get("employee_role"))

        operator = chat_store.get_latest_thread_for_workspace(
            "workspace_dashpro",
            thread_kind="operator",
        )
        self.assertIsNotNone(operator)
        op_msgs = chat_store.list_thread_messages(str(operator["thread_id"]))
        self.assertTrue(
            any(
                str(m.get("content") or "").startswith("VAXON:")
                and "Dana" in str(m.get("content") or "")
                and "lead" in str(m.get("content") or "").lower()
                and "run_dana_lead_1" in str(m.get("content") or "")
                for m in op_msgs
                if m.get("role") == "agent"
            )
        )
