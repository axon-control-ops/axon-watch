"""Lead plan read API — workspace list with task mappings."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from tests.support.control_plane_app_loader import prepare_control_plane_imports
from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


class LeadPlanReadApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = prepare_control_plane_imports()
        self.addCleanup(self._restore)
        from app.main import app
        from app.persistence import run_store

        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)

    def _restore(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.modules.update(self._saved)

    def test_list_workspace_lead_plans_includes_task_links(self) -> None:
        from app.workspace_agents.lead_fan_out import materialize_lead_fan_out

        created = materialize_lead_fan_out(
            workspace_id="workspace_axon_watch",
            goal="Check with all sub-agents whether Gate 5 fan-out is wired",
            mode="auto",
            create_runs=False,
        )
        plan_id = str(created.get("plan_id") or "")
        self.assertTrue(plan_id)

        response = self.client.get("/api/workspaces/workspace_axon_watch/lead/plans")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("workspace_axon_watch", payload["workspace_id"])
        self.assertGreaterEqual(payload["count"], 1)
        match = next(item for item in payload["items"] if item["plan_id"] == plan_id)
        self.assertTrue(match["task_links"])
        self.assertEqual(len(match["task_ids"]), len(match["task_links"]))

        detail = self.client.get(f"/api/lead/plans/{plan_id}")
        self.assertEqual(200, detail.status_code)
        self.assertEqual(plan_id, detail.json()["plan_id"])
        self.assertIn("task_links", detail.json())

    def test_plan_detail_vaxon_handoff_is_none_before_synthesis_posted(self) -> None:
        from app.workspace_agents.lead_fan_out import materialize_lead_fan_out

        created = materialize_lead_fan_out(
            workspace_id="workspace_axon_watch",
            goal="Check whether the rollup navigation regression test is wired",
            mode="auto",
            create_runs=False,
        )
        plan_id = str(created.get("plan_id") or "")

        detail = self.client.get(f"/api/lead/plans/{plan_id}")
        self.assertEqual(200, detail.status_code)
        self.assertIsNone(detail.json()["vaxon_handoff"])

    def test_plan_detail_vaxon_handoff_points_at_the_posted_rollup_message(self) -> None:
        from app.workspace_agents.lead_fan_out import materialize_lead_fan_out
        from app.workspace_agents.lead_vaxon_handoff import post_lead_synthesis_to_vaxon

        created = materialize_lead_fan_out(
            workspace_id="workspace_axon_watch",
            goal="Check whether Review now can find its rollup message",
            mode="auto",
            create_runs=False,
        )
        plan_id = str(created.get("plan_id") or "")

        posted = post_lead_synthesis_to_vaxon(
            plan_id=plan_id,
            workspace_id="workspace_axon_watch",
            goal="Check whether Review now can find its rollup message",
            summary="All specialists reported in; nothing blocking.",
            findings=[],
        )

        detail = self.client.get(f"/api/lead/plans/{plan_id}")
        self.assertEqual(200, detail.status_code)
        handoff = detail.json()["vaxon_handoff"]
        self.assertIsNotNone(handoff)
        self.assertEqual(posted["thread_id"], handoff["thread_id"])
        self.assertEqual(posted["message_id"], handoff["message_id"])


if __name__ == "__main__":
    unittest.main()
