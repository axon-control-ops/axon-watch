from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402

_ACTIVE_RUN_KEYS = {
    "run_id",
    "workspace_id",
    "mode",
    "status",
    "phase",
    "title",
    "detail",
    "lane_id",
    "updated_at",
}


class RuntimeSummaryActiveRunsTests(unittest.TestCase):
    def setUp(self) -> None:
        run_store.reset_store()
        self.client = TestClient(app)

    def test_runtime_summary_includes_active_run_after_create(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Active summary run",
                "detail": "Visible in runtime summary",
            },
        ).json()

        with patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-03T15:00:00Z"),
        ):
            response = self.client.get("/api/runtime/summary")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(1, len(payload["active_runs"]))
        active_run = payload["active_runs"][0]
        self.assertEqual(_ACTIVE_RUN_KEYS, set(active_run))
        self.assertEqual(created["run_id"], active_run["run_id"])
        self.assertEqual("executing", active_run["phase"])
        self.assertEqual("running", active_run["status"])
        self.assertEqual("Active summary run", active_run["title"])

    def test_runtime_summary_clears_active_run_after_complete(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Completable summary run",
            },
        ).json()
        self.client.post(f"/api/runs/{created['run_id']}/complete")

        with patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-03T15:00:00Z"),
        ):
            response = self.client.get("/api/runtime/summary")

        payload = response.json()
        self.assertEqual([], payload["active_runs"])


if __name__ == "__main__":
    unittest.main()
