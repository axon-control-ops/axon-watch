from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import handoff_store, run_store  # noqa: E402


class ControlPlaneWorkspaceHandoffsTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        handoff_store.reset_store()
        self.addCleanup(handoff_store.reset_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_create_handoff_returns_target_workspace_summary(self) -> None:
        response = self.client.post(
            "/api/workspaces/workspace_smoke/handoffs",
            json={
                "target_workspace_id": "workspace_alpha",
                "task": "Review bootstrap follow-up",
                "reason": "Cross-workspace verification",
            },
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()

        handoff = payload["handoff"]
        self.assertEqual("workspace_smoke", handoff["source_workspace_id"])
        self.assertEqual("workspace_alpha", handoff["target_workspace_id"])
        self.assertEqual("recorded", handoff["status"])
        self.assertTrue(handoff["handoff_id"].startswith("handoff-"))

        summary = payload["target_workspace_summary"]
        self.assertEqual("workspace_alpha", summary["workspace_id"])
        self.assertEqual("isolated_root", summary["connection_kind"])
        self.assertIn("run_count", summary)
        self.assertIn("active_run_count", summary)
        self.assertIn("active_runs", summary)

    def test_list_handoffs_returns_recorded_handoff(self) -> None:
        create_response = self.client.post(
            "/api/workspaces/workspace_smoke/handoffs",
            json={
                "target_workspace_id": "workspace_alpha",
                "task": "Follow-up task",
            },
        )
        handoff_id = create_response.json()["handoff"]["handoff_id"]

        list_response = self.client.get("/api/workspaces/workspace_smoke/handoffs")
        self.assertEqual(200, list_response.status_code)
        items = list_response.json()["items"]
        self.assertEqual(1, len(items))
        self.assertEqual(handoff_id, items[0]["handoff_id"])

    def test_create_handoff_rejects_unknown_target(self) -> None:
        response = self.client.post(
            "/api/workspaces/workspace_smoke/handoffs",
            json={
                "target_workspace_id": "workspace_missing",
                "task": "Should fail",
            },
        )
        self.assertEqual(404, response.status_code)

    def test_create_handoff_rejects_same_source_and_target(self) -> None:
        response = self.client.post(
            "/api/workspaces/workspace_smoke/handoffs",
            json={
                "target_workspace_id": "workspace_smoke",
                "task": "Should fail",
            },
        )
        self.assertEqual(400, response.status_code)


if __name__ == "__main__":
    unittest.main()
