from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402


class ControlPlaneRunsTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

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

    def test_create_run_can_stop_at_awaiting_approval(self) -> None:
        response = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Guarded run",
                "detail": "Needs operator approval",
                "requires_approval": True,
            },
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("awaiting_approval", payload["phase"])
        self.assertEqual("blocked", payload["status"])
        self.assertTrue(payload["can_stop"])
        self.assertFalse(payload["can_resume"])
        self.assertTrue(payload["can_approve"])
        self.assertEqual("Awaiting operator approval", payload["current_step"])

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

    def test_complete_requires_executing_or_review_ready_phase(self) -> None:
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

    def test_stop_run_pauses_executing_run(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Stoppable run",
            },
        ).json()

        stop_response = self.client.post(f"/api/runs/{created['run_id']}/stop")
        self.assertEqual(200, stop_response.status_code)
        stopped = stop_response.json()
        self.assertEqual("paused", stopped["phase"])
        self.assertEqual("waiting", stopped["status"])
        self.assertTrue(stopped["can_stop"])
        self.assertTrue(stopped["can_resume"])
        self.assertEqual("Run paused by operator stop", stopped["current_step"])

        history = run_store.list_history(stopped["history_ref"])
        self.assertEqual("operator_stop", history[-1]["receipt"]["type"])

    def test_complete_paused_run_transitions_to_completed(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Paused completable run",
            },
        ).json()
        self.client.post(f"/api/runs/{created['run_id']}/stop")

        complete_response = self.client.post(f"/api/runs/{created['run_id']}/complete")
        self.assertEqual(200, complete_response.status_code)
        completed = complete_response.json()
        self.assertEqual("completed", completed["phase"])
        self.assertEqual("done", completed["status"])

    def test_resume_run_returns_paused_run_to_executing(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Resumable run",
            },
        ).json()
        paused = self.client.post(f"/api/runs/{created['run_id']}/stop").json()

        resume_response = self.client.post(f"/api/runs/{created['run_id']}/resume")
        self.assertEqual(200, resume_response.status_code)
        resumed = resume_response.json()
        self.assertEqual("executing", resumed["phase"])
        self.assertEqual("running", resumed["status"])
        self.assertTrue(resumed["can_stop"])
        self.assertFalse(resumed["can_resume"])

        history = run_store.list_history(paused["history_ref"])
        self.assertEqual("operator_resume", history[-1]["receipt"]["type"])

    def test_resume_from_awaiting_approval_fails(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Approval-guarded run",
                "requires_approval": True,
            },
        ).json()

        resume_response = self.client.post(f"/api/runs/{created['run_id']}/resume")
        self.assertEqual(400, resume_response.status_code)
        self.assertIn("awaiting_approval", resume_response.json()["detail"])

        show_response = self.client.get(f"/api/runs/{created['run_id']}")
        self.assertEqual("awaiting_approval", show_response.json()["phase"])

    def test_approve_run_moves_awaiting_approval_to_executing(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Awaiting approval run",
                "requires_approval": True,
            },
        ).json()

        approve_response = self.client.post(f"/api/runs/{created['run_id']}/approve")
        self.assertEqual(200, approve_response.status_code)
        approved = approve_response.json()
        self.assertEqual("executing", approved["phase"])
        self.assertEqual("running", approved["status"])
        self.assertFalse(approved["can_approve"])
        self.assertEqual("Run approved by operator", approved["current_step"])

        history = run_store.list_history(approved["history_ref"])
        self.assertEqual("operator_approve", history[-1]["receipt"]["type"])

    def test_reject_run_moves_awaiting_approval_to_cancelled(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Rejectable run",
                "requires_approval": True,
            },
        ).json()

        reject_response = self.client.post(f"/api/runs/{created['run_id']}/reject")
        self.assertEqual(200, reject_response.status_code)
        rejected = reject_response.json()
        self.assertEqual("cancelled", rejected["phase"])
        self.assertEqual("stopped", rejected["status"])
        self.assertFalse(rejected["can_stop"])
        self.assertFalse(rejected["can_resume"])
        self.assertFalse(rejected["can_approve"])

        history = run_store.list_history(rejected["history_ref"])
        self.assertEqual("operator_reject", history[-1]["receipt"]["type"])

    def test_stop_run_cancels_awaiting_approval_run(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Stop guarded run",
                "requires_approval": True,
            },
        ).json()

        stop_response = self.client.post(f"/api/runs/{created['run_id']}/stop")
        self.assertEqual(200, stop_response.status_code)
        cancelled = stop_response.json()
        self.assertEqual("cancelled", cancelled["phase"])
        self.assertEqual("stopped", cancelled["status"])
        self.assertFalse(cancelled["can_stop"])
        self.assertFalse(cancelled["can_resume"])

    def test_approve_requires_awaiting_approval_phase(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Already executing run",
            },
        ).json()

        approve_response = self.client.post(f"/api/runs/{created['run_id']}/approve")
        reject_response = self.client.post(f"/api/runs/{created['run_id']}/reject")
        self.assertEqual(400, approve_response.status_code)
        self.assertEqual(400, reject_response.status_code)

    def test_stop_run_cancels_paused_run(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Pause then cancel run",
            },
        ).json()
        paused = self.client.post(f"/api/runs/{created['run_id']}/stop").json()

        stop_again_response = self.client.post(f"/api/runs/{created['run_id']}/stop")
        self.assertEqual(200, stop_again_response.status_code)
        cancelled = stop_again_response.json()
        self.assertEqual("paused", paused["phase"])
        self.assertEqual("cancelled", cancelled["phase"])
        self.assertEqual("stopped", cancelled["status"])
        self.assertFalse(cancelled["can_stop"])
        self.assertFalse(cancelled["can_resume"])

    def test_runs_persist_across_new_client_instances(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Persistent run",
            },
        ).json()

        self.client.close()
        second_client = TestClient(app)
        self.addCleanup(second_client.close)

        listed = second_client.get("/api/runs").json()
        self.assertEqual(1, listed["count"])
        self.assertEqual(created["run_id"], listed["items"][0]["run_id"])

    def test_mark_review_ready_transitions_executing_to_review_ready(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Reviewable run",
                "detail": "Work ready for operator review",
            },
        ).json()

        review_response = self.client.post(f"/api/runs/{created['run_id']}/review-ready")
        self.assertEqual(200, review_response.status_code)
        reviewed = review_response.json()
        self.assertEqual("review_ready", reviewed["phase"])
        self.assertEqual("review", reviewed["status"])
        self.assertFalse(reviewed["can_stop"])
        self.assertTrue(reviewed["can_resume"])
        self.assertTrue(reviewed["can_review"])
        self.assertFalse(reviewed["can_approve"])
        self.assertIsNone(reviewed["ended_at"])
        self.assertEqual("Awaiting operator review", reviewed["current_step"])

        history = run_store.list_history(reviewed["history_ref"])
        self.assertEqual("review_ready", history[-1]["receipt"]["type"])
        self.assertEqual("executing", history[-1]["from_phase"])
        self.assertEqual("review_ready", history[-1]["to_phase"])

    def test_mark_review_ready_requires_executing_phase(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Already completed run",
            },
        ).json()
        self.client.post(f"/api/runs/{created['run_id']}/complete")

        repeat_response = self.client.post(f"/api/runs/{created['run_id']}/review-ready")
        self.assertEqual(400, repeat_response.status_code)
        self.assertIn("executing", repeat_response.json()["detail"])

    def test_mark_review_ready_rejects_awaiting_approval(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Approval-guarded run",
                "requires_approval": True,
            },
        ).json()

        review_response = self.client.post(f"/api/runs/{created['run_id']}/review-ready")
        self.assertEqual(400, review_response.status_code)
        self.assertIn("awaiting_approval", review_response.json()["detail"])

        show_response = self.client.get(f"/api/runs/{created['run_id']}")
        self.assertEqual("awaiting_approval", show_response.json()["phase"])

    def test_resume_from_review_ready_returns_to_executing(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Review-ready run",
                "detail": "Resume for follow-up work",
            },
        ).json()
        review_ready = self.client.post(f"/api/runs/{created['run_id']}/review-ready").json()
        self.assertEqual("review_ready", review_ready["phase"])

        resume_response = self.client.post(f"/api/runs/{created['run_id']}/resume")
        self.assertEqual(200, resume_response.status_code)
        resumed = resume_response.json()
        self.assertEqual("executing", resumed["phase"])
        self.assertEqual("Run resumed for follow-up work", resumed["current_step"])
        self.assertFalse(resumed["can_review"])

    def test_resume_one_shot_review_ready_completes_instead_of_executing(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "git status",
            },
        ).json()
        review_ready = self.client.post(f"/api/runs/{created['run_id']}/review-ready").json()
        self.assertEqual("review_ready", review_ready["phase"])

        resume_response = self.client.post(f"/api/runs/{created['run_id']}/resume")
        self.assertEqual(200, resume_response.status_code)
        completed = resume_response.json()
        self.assertEqual("completed", completed["phase"])
        self.assertEqual("done", completed["status"])
        self.assertFalse(completed["can_resume"])

        history = run_store.list_history(str(completed["history_ref"]))
        self.assertEqual("operator_complete", history[-1]["receipt"]["type"])
        self.assertIn("One-shot", history[-1]["receipt"]["summary"])

    def test_complete_from_review_ready_transitions_to_completed(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Review completion run",
            },
        ).json()
        self.client.post(f"/api/runs/{created['run_id']}/review-ready")

        complete_response = self.client.post(f"/api/runs/{created['run_id']}/complete")
        self.assertEqual(200, complete_response.status_code)
        completed = complete_response.json()
        self.assertEqual("completed", completed["phase"])
        self.assertEqual("done", completed["status"])
        self.assertIsNotNone(completed["ended_at"])

        history = run_store.list_history(completed["history_ref"])
        self.assertEqual("operator_complete", history[-1]["receipt"]["type"])
        self.assertEqual("review_ready", history[-1]["from_phase"])
        self.assertEqual("completed", history[-1]["to_phase"])

    def test_executing_and_awaiting_approval_runs_coexist_in_api(self) -> None:
        executing = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Active executing run",
            },
        ).json()
        approval = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Guarded run",
                "requires_approval": True,
            },
        ).json()

        list_response = self.client.get("/api/runs")
        self.assertEqual(200, list_response.status_code)
        phases = {item["run_id"]: item["phase"] for item in list_response.json()["items"]}
        self.assertEqual("executing", phases[executing["run_id"]])
        self.assertEqual("awaiting_approval", phases[approval["run_id"]])

        resume_response = self.client.post(f"/api/runs/{approval['run_id']}/resume")
        self.assertEqual(400, resume_response.status_code)

        approve_response = self.client.post(f"/api/runs/{approval['run_id']}/approve")
        self.assertEqual(200, approve_response.status_code)
        self.assertEqual("executing", approve_response.json()["phase"])

    def test_get_run_history_returns_transition_receipts(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "History run",
            },
        ).json()
        stopped = self.client.post(f"/api/runs/{created['run_id']}/stop").json()

        response = self.client.get(f"/api/runs/{created['run_id']}/history")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(created["run_id"], payload["run_id"])
        self.assertEqual(stopped["history_ref"], payload["history_ref"])
        self.assertGreaterEqual(payload["count"], 2)
        self.assertEqual(payload["count"], len(payload["items"]))
        self.assertEqual("operator_stop", payload["items"][-1]["receipt"]["type"])

    def test_get_run_history_returns_404_for_missing_run(self) -> None:
        response = self.client.get("/api/runs/run_missing/history")
        self.assertEqual(404, response.status_code)

    def test_show_missing_run_returns_404(self) -> None:
        response = self.client.get("/api/runs/run_missing")
        self.assertEqual(404, response.status_code)


if __name__ == "__main__":
    unittest.main()
