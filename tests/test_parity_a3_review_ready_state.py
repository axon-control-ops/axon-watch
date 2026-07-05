"""P-A3 review-ready cross-surface parity tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.command_executor import execute_resume_from_review  # noqa: E402
from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402


def _watch_probe_ok() -> tuple[bool, str, None, str]:
    return (True, "ok", None, "2026-07-05T10:00:00Z")


class ParityA3ReviewReadyStateTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def _create_executing_run(self) -> dict[str, object]:
        response = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_smoke",
                "mode": "agent",
                "summary": "P-A3 review-ready parity run",
            },
        )
        self.assertEqual(200, response.status_code)
        return response.json()

    def _runtime_payload(self) -> dict[str, object]:
        with patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=_watch_probe_ok(),
        ):
            response = self.client.get("/api/runtime/summary")
        self.assertEqual(200, response.status_code)
        return response.json()

    def _mark_review_ready(self, run_id: str) -> dict[str, object]:
        response = self.client.post(f"/api/runs/{run_id}/review-ready")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("review_ready", payload["phase"])
        self.assertEqual("review", payload["status"])
        self.assertTrue(payload["can_review"])
        self.assertTrue(payload["can_resume"])
        self.assertFalse(payload["can_stop"])
        return payload

    def _assert_review_ready_surfaces(self, run_id: str) -> None:
        show = self.client.get(f"/api/runs/{run_id}").json()
        listed = next(
            item for item in self.client.get("/api/runs").json()["items"] if item["run_id"] == run_id
        )
        summary = self._runtime_payload()
        briefing = self.client.get("/api/briefing").json()

        for surface in (show, listed):
            self.assertEqual("review_ready", surface["phase"])
            self.assertEqual("review", surface["status"])
            self.assertTrue(surface["can_review"])

        active = summary["active_runs"][0]
        self.assertEqual(run_id, active["run_id"])
        self.assertEqual("review_ready", active["phase"])
        self.assertEqual("review", active["status"])

        briefing_run = briefing["active_runs"][0]
        self.assertEqual(run_id, briefing_run["run_id"])
        self.assertEqual("review_ready", briefing_run["phase"])
        self.assertIn("review", briefing["notice"].lower())

    def test_review_ready_cross_surface_and_resume_paths(self) -> None:
        created = self._create_executing_run()
        run_id = str(created["run_id"])

        self._mark_review_ready(run_id)
        self._assert_review_ready_surfaces(run_id)

        history = self.client.get(f"/api/runs/{run_id}/history").json()["items"]
        self.assertEqual("review_ready", history[-1]["receipt"]["type"])

        resume_response = self.client.post(f"/api/runs/{run_id}/resume")
        self.assertEqual(200, resume_response.status_code)
        resumed = resume_response.json()
        self.assertEqual("executing", resumed["phase"])
        self.assertFalse(resumed["can_review"])

        execution = execute_resume_from_review("workspace_smoke")
        self.assertFalse(execution.success)

        self._mark_review_ready(run_id)
        execution = execute_resume_from_review("workspace_smoke")
        self.assertTrue(execution.success)
        self.assertEqual(run_id, execution.run_id)

        show = self.client.get(f"/api/runs/{run_id}").json()
        self.assertEqual("executing", show["phase"])

    def test_complete_from_review_ready_cross_surface(self) -> None:
        created = self._create_executing_run()
        run_id = str(created["run_id"])
        self._mark_review_ready(run_id)

        complete_response = self.client.post(f"/api/runs/{run_id}/complete")
        self.assertEqual(200, complete_response.status_code)
        completed = complete_response.json()
        self.assertEqual("completed", completed["phase"])

        summary = self._runtime_payload()
        self.assertEqual([], summary["active_runs"])

        history = self.client.get(f"/api/runs/{run_id}/history").json()["items"]
        self.assertEqual("operator_complete", history[-1]["receipt"]["type"])
        self.assertEqual("review_ready", history[-1]["from_phase"])


if __name__ == "__main__":
    unittest.main()
