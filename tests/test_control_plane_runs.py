from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402


class ControlPlaneRunsTests(unittest.TestCase):
    def setUp(self) -> None:
        run_store.reset_store()
        self.client = TestClient(app)

    def test_create_run_stops_at_executing(self) -> None:
        response = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Thin-slice run",
                "detail": "Run lifecycle bootstrap",
            },
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("executing", payload["phase"])
        self.assertEqual("running", payload["status"])
        self.assertTrue(payload["can_stop"])
        self.assertFalse(payload["can_resume"])
        self.assertIsNone(payload["ended_at"])
        self.assertEqual("Executing thin-slice work", payload["current_step"])

    def test_list_and_show_run(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Listed run",
            },
        ).json()

        list_response = self.client.get("/api/runs")
        self.assertEqual(200, list_response.status_code)
        listed = list_response.json()
        self.assertEqual(1, listed["count"])
        self.assertEqual(created["run_id"], listed["items"][0]["run_id"])

        show_response = self.client.get(f"/api/runs/{created['run_id']}")
        self.assertEqual(200, show_response.status_code)
        self.assertEqual(created["run_id"], show_response.json()["run_id"])

    def test_complete_run_transitions_to_completed(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Completable run",
            },
        ).json()

        complete_response = self.client.post(f"/api/runs/{created['run_id']}/complete")
        self.assertEqual(200, complete_response.status_code)
        completed = complete_response.json()
        self.assertEqual("completed", completed["phase"])
        self.assertEqual("done", completed["status"])
        self.assertIsNotNone(completed["ended_at"])
        self.assertFalse(completed["can_stop"])

    def test_complete_requires_executing_phase(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Already completed run",
            },
        ).json()
        self.client.post(f"/api/runs/{created['run_id']}/complete")

        repeat_response = self.client.post(f"/api/runs/{created['run_id']}/complete")
        self.assertEqual(400, repeat_response.status_code)

    def test_show_missing_run_returns_404(self) -> None:
        response = self.client.get("/api/runs/run_missing")
        self.assertEqual(404, response.status_code)


if __name__ == "__main__":
    unittest.main()
