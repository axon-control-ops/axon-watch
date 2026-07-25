"""P-A2 approval boundary cross-surface parity tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.orchestration import orchestrate_command_run  # noqa: E402
from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402


def _watch_probe_ok() -> tuple[bool, str, None, str]:
    return (True, "ok", None, "2026-07-05T10:00:00Z")


class ParityA2ApprovalBoundariesTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def _create_approval_run(self) -> dict[str, object]:
        response = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_smoke",
                "mode": "agent",
                "summary": "P-A2 approval boundary run",
                "requires_approval": True,
            },
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("awaiting_approval", payload["phase"])
        self.assertTrue(payload["can_approve"])
        self.assertFalse(payload["can_resume"])
        return payload

    def _runtime_payload(self) -> dict[str, object]:
        with patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=_watch_probe_ok(),
        ):
            response = self.client.get("/api/runtime/summary")
        self.assertEqual(200, response.status_code)
        return response.json()

    def _assert_pending_boundary(self, run_id: str) -> None:
        show = self.client.get(f"/api/runs/{run_id}").json()
        listed = next(
            item for item in self.client.get("/api/runs").json()["items"] if item["run_id"] == run_id
        )
        summary = self._runtime_payload()
        briefing = self.client.get("/api/briefing").json()

        for surface in (show, listed):
            with self.subTest(surface="run_record"):
                self.assertEqual("awaiting_approval", surface["phase"])
                self.assertEqual("blocked", surface["status"])
                self.assertTrue(surface["can_approve"])
                self.assertFalse(surface["can_resume"])

        active_runs = summary["active_runs"]
        self.assertEqual(1, len(active_runs))
        self.assertEqual(run_id, active_runs[0]["run_id"])
        self.assertEqual("awaiting_approval", active_runs[0]["phase"])
        self.assertEqual("blocked", active_runs[0]["status"])
        self.assertEqual(1, summary["approvals"]["pending_count"])

        self.assertEqual(1, briefing["pending_approvals"]["count"])
        self.assertEqual("awaiting_approval", briefing["active_runs"][0]["phase"])
        self.assertEqual("approve_run", briefing["next_safe_actions"][0]["kind"])
        self.assertEqual(run_id, briefing["next_safe_actions"][0]["run_id"])
        self.assertIn("approval", briefing["notice"].lower())

    def test_approval_boundary_blocks_execution_until_approve(self) -> None:
        created = self._create_approval_run()
        run_id = str(created["run_id"])

        self._assert_pending_boundary(run_id)

        resume_response = self.client.post(f"/api/runs/{run_id}/resume")
        self.assertEqual(400, resume_response.status_code)
        self.assertIn("awaiting_approval", resume_response.json()["detail"])

        complete_response = self.client.post(f"/api/runs/{run_id}/complete")
        self.assertEqual(400, complete_response.status_code)
        self.assertIn("awaiting_approval", complete_response.json()["detail"])

        record, execution = orchestrate_command_run(
            workspace_id="workspace_smoke",
            content="git status",
            run_record=created,
            dispatched=True,
        )
        self.assertIsNone(execution)
        self.assertEqual("awaiting_approval", record["phase"])

        approve_response = self.client.post(f"/api/runs/{run_id}/approve")
        self.assertEqual(200, approve_response.status_code)
        approved = approve_response.json()
        self.assertEqual("executing", approved["phase"])
        self.assertFalse(approved["can_approve"])

        summary = self._runtime_payload()
        briefing = self.client.get("/api/briefing").json()
        self.assertEqual(0, summary["approvals"]["pending_count"])
        self.assertEqual(0, briefing["pending_approvals"]["count"])
        self.assertEqual("executing", summary["active_runs"][0]["phase"])

        history = self.client.get(f"/api/runs/{run_id}/history").json()["items"]
        self.assertEqual("operator_approve", history[-1]["receipt"]["type"])

    def test_reject_clears_approval_boundary(self) -> None:
        created = self._create_approval_run()
        run_id = str(created["run_id"])

        reject_response = self.client.post(f"/api/runs/{run_id}/reject")
        self.assertEqual(200, reject_response.status_code)
        rejected = reject_response.json()
        self.assertEqual("cancelled", rejected["phase"])
        self.assertFalse(rejected["can_approve"])

        summary = self._runtime_payload()
        briefing = self.client.get("/api/briefing").json()
        self.assertEqual(0, summary["approvals"]["pending_count"])
        self.assertEqual(0, briefing["pending_approvals"]["count"])
        self.assertEqual([], summary["active_runs"])

        history = self.client.get(f"/api/runs/{run_id}/history").json()["items"]
        self.assertEqual("operator_reject", history[-1]["receipt"]["type"])


if __name__ == "__main__":
    unittest.main()
