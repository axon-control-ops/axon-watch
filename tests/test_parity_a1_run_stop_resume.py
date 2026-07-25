"""P-A1 run stop/resume cross-surface parity tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402


def _watch_probe_ok() -> tuple[bool, str, None, str]:
    return (True, "ok", None, "2026-07-05T10:00:00Z")


class ParityA1RunStopResumeTests(unittest.TestCase):
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
                "summary": "P-A1 stop/resume parity run",
            },
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("executing", payload["phase"])
        return payload

    def _runtime_active_run(self) -> dict[str, object]:
        with patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=_watch_probe_ok(),
        ):
            response = self.client.get("/api/runtime/summary")
        self.assertEqual(200, response.status_code)
        active_runs = response.json()["active_runs"]
        self.assertEqual(1, len(active_runs))
        return active_runs[0]

    def _assert_run_surfaces_match(self, run_id: str, expected: dict[str, object]) -> None:
        show = self.client.get(f"/api/runs/{run_id}").json()
        listed = next(
            item for item in self.client.get("/api/runs").json()["items"] if item["run_id"] == run_id
        )
        summary = self._runtime_active_run()

        for surface_name, surface in (("show", show), ("list", listed)):
            with self.subTest(surface=surface_name, phase=expected["phase"]):
                self.assertEqual(expected["phase"], surface["phase"])
                self.assertEqual(expected["status"], surface["status"])
                if "can_stop" in expected:
                    self.assertEqual(expected["can_stop"], surface["can_stop"])
                if "can_resume" in expected:
                    self.assertEqual(expected["can_resume"], surface["can_resume"])

        with self.subTest(surface="summary", phase=expected["phase"]):
            self.assertEqual(expected["phase"], summary["phase"])
            self.assertEqual(expected["status"], summary["status"])
            self.assertEqual(run_id, summary["run_id"])

    def test_stop_resume_cross_surface_consistency_and_receipts(self) -> None:
        created = self._create_executing_run()
        run_id = str(created["run_id"])

        stop_response = self.client.post(f"/api/runs/{run_id}/stop")
        self.assertEqual(200, stop_response.status_code)

        self._assert_run_surfaces_match(
            run_id,
            {
                "phase": "paused",
                "status": "waiting",
                "can_stop": True,
                "can_resume": True,
            },
        )

        history_after_stop = self.client.get(f"/api/runs/{run_id}/history").json()["items"]
        self.assertEqual("operator_stop", history_after_stop[-1]["receipt"]["type"])

        resume_response = self.client.post(f"/api/runs/{run_id}/resume")
        self.assertEqual(200, resume_response.status_code)

        self._assert_run_surfaces_match(
            run_id,
            {
                "phase": "executing",
                "status": "running",
                "can_stop": True,
                "can_resume": False,
            },
        )

        history_after_resume = self.client.get(f"/api/runs/{run_id}/history").json()["items"]
        self.assertEqual("operator_stop", history_after_resume[-2]["receipt"]["type"])
        self.assertEqual("operator_resume", history_after_resume[-1]["receipt"]["type"])


if __name__ == "__main__":
    unittest.main()
