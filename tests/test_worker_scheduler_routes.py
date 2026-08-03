"""HTTP route tests for fleet / continuous-worker scheduler controls."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402


class WorkerSchedulerRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_worker_scheduler_get_defaults_off(self) -> None:
        response = self.client.get("/api/worker-scheduler")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertFalse(payload["scheduler_enabled"])
        self.assertFalse(payload["effective_enabled"])
        # Test DB isolation disables the env brake so the scheduler loop never starts.
        self.assertFalse(payload["env_allowed"])
        self.assertTrue(payload["blocked_by_env"])
        self.assertEqual(1, payload["max_active"])
        self.assertEqual(1, payload["max_starts_per_tick"])
        self.assertEqual(0, payload["executing_count"])
        self.assertEqual({}, payload["employee_enabled"])

    def test_worker_scheduler_patch_and_env_brake(self) -> None:
        with patch.dict(os.environ, {"AXON_WATCH_WORKER_SCHEDULER": "0"}, clear=False):
            response = self.client.patch(
                "/api/worker-scheduler",
                json={
                    "scheduler_enabled": True,
                    "max_active": 3,
                    "max_starts_per_tick": 1,
                },
            )
            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertTrue(payload["scheduler_enabled"])
            self.assertTrue(payload["blocked_by_env"])
            self.assertFalse(payload["effective_enabled"])
            self.assertEqual(3, payload["max_active"])
            self.assertEqual(1, payload["max_starts_per_tick"])

        with patch.dict(os.environ, {"AXON_WATCH_WORKER_SCHEDULER": "1"}, clear=False):
            response = self.client.get("/api/worker-scheduler")
            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertTrue(payload["scheduler_enabled"])
            self.assertTrue(payload["effective_enabled"])

    def test_worker_scheduler_patch_empty_body_rejected(self) -> None:
        response = self.client.patch("/api/worker-scheduler", json={})
        self.assertEqual(400, response.status_code)
        self.assertIn("no worker scheduler fields", response.json()["detail"])

    def test_worker_scheduler_status_exposes_dispatch_only_usage_policy(self) -> None:
        response = self.client.get("/api/worker-scheduler")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertFalse(payload["cursor_usage_on_idle_tick"])
        self.assertEqual("dispatch_only", payload["cursor_usage_policy"])

    def test_worker_scheduler_hard_kill_pauses_and_demotes_to_semi(self) -> None:
        from app.persistence import operator_presence_settings_store

        operator_presence_settings_store.save_settings(
            {**operator_presence_settings_store.load_settings(), "autonomy_mode": "full"}
        )
        with patch.dict(os.environ, {"AXON_WATCH_WORKER_SCHEDULER": "1"}, clear=False):
            enabled = self.client.patch(
                "/api/worker-scheduler",
                json={"scheduler_enabled": True},
            )
            self.assertEqual(200, enabled.status_code)
            self.assertTrue(enabled.json()["scheduler_enabled"])

            created = self.client.post(
                "/api/runs",
                json={
                    "workspace_id": "workspace_sched_demo",
                    "mode": "agent",
                    "summary": "Active worker run",
                    "employee_role": "backend",
                },
            )
            self.assertEqual(200, created.status_code)
            run_id = created.json()["run_id"]

            response = self.client.post("/api/worker-scheduler/hard-kill")
            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertTrue(payload["hard_killed"])
            self.assertFalse(payload["scheduler_enabled"])
            self.assertFalse(payload["effective_enabled"])
            self.assertIn(run_id, payload["stopped_run_ids"])

            presence = operator_presence_settings_store.load_settings()
            self.assertEqual("semi", presence.get("autonomy_mode"))

    def test_worker_scheduler_resume_reenables_without_env_edit(self) -> None:
        from app.persistence import operator_presence_settings_store

        operator_presence_settings_store.save_settings(
            {**operator_presence_settings_store.load_settings(), "autonomy_mode": "semi"}
        )
        with (
            patch.dict(os.environ, {"AXON_WATCH_WORKER_SCHEDULER": "1"}, clear=False),
            patch(
                "app.workspace_agents.fleet_control.run_continuous_worker_tick",
                return_value=[{"run_id": "run_queued"}],
            ) as dispatch_tick,
        ):
            self.client.patch("/api/worker-scheduler", json={"scheduler_enabled": False})
            response = self.client.post("/api/worker-scheduler/resume")
            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertTrue(payload["resumed"])
            self.assertTrue(payload["scheduler_enabled"])
            self.assertTrue(payload["effective_enabled"])
            self.assertFalse(payload["blocked_by_env"])
            self.assertEqual(["run_queued"], payload["started_run_ids"])
            dispatch_tick.assert_called_once_with()

            presence = operator_presence_settings_store.load_settings()
            self.assertEqual("full", presence.get("autonomy_mode"))

    def test_worker_scheduler_stop_active_stops_executing_runs(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_sched_demo",
                "mode": "agent",
                "summary": "Active worker run",
                "employee_role": "backend",
            },
        )
        self.assertEqual(200, created.status_code)
        run_id = created.json()["run_id"]

        response = self.client.post("/api/worker-scheduler/stop-active")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertIn(run_id, payload["stopped_run_ids"])
        self.assertEqual([], payload["stop_errors"])
        self.assertEqual(0, payload["executing_count"])

        stored = run_store.get_run(run_id)
        assert stored is not None
        self.assertEqual("paused", stored["phase"])

    def test_stop_active_skips_untagged_operator_runs(self) -> None:
        worker = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_sched_demo",
                "mode": "agent",
                "summary": "Backend continuous shift",
                "employee_role": "backend",
            },
        )
        operator = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_sched_demo",
                "mode": "agent",
                "summary": "Operator chat run",
            },
        )
        self.assertEqual(200, worker.status_code)
        self.assertEqual(200, operator.status_code)
        worker_id = worker.json()["run_id"]
        operator_id = operator.json()["run_id"]

        response = self.client.post("/api/worker-scheduler/stop-active")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertIn(worker_id, payload["stopped_run_ids"])
        self.assertNotIn(operator_id, payload["stopped_run_ids"])

        worker_stored = run_store.get_run(worker_id)
        operator_stored = run_store.get_run(operator_id)
        assert worker_stored is not None
        assert operator_stored is not None
        self.assertEqual("paused", worker_stored["phase"])
        self.assertEqual("executing", operator_stored["phase"])

    def test_worker_scheduler_status_counts_only_employee_shifts(self) -> None:
        self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_sched_demo",
                "mode": "agent",
                "summary": "Backend continuous shift",
                "employee_role": "backend",
            },
        )
        self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_sched_demo",
                "mode": "agent",
                "summary": "Operator chat run",
            },
        )
        response = self.client.get("/api/worker-scheduler")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(1, payload["executing_count"])
        self.assertEqual(1, payload["active_run_count"])

    def test_workspace_employee_enabled_patch_updates_roster(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            project_root = Path(tempdir) / "bound-project"
            project_root.mkdir()
            bindings_file = Path(tempdir) / "bindings.json"
            agents_file = Path(tempdir) / "agents.json"
            bindings_file.write_text(
                json.dumps(
                    {
                        "bindings": {
                            "workspace_sched_demo": {
                                "project_root": str(project_root),
                                "display_name": "Sched Co",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            agents_file.write_text(
                json.dumps(
                    {
                        "companies": {
                            "workspace_sched_demo": {
                                "company_name": "Sched Co",
                                "employees": [
                                    {
                                        "name": "Sched UI",
                                        "role": "frontend",
                                        "schedule": "continuous",
                                    },
                                ],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "AXON_WATCH_WORKSPACE_BINDINGS_FILE": str(bindings_file),
                    "AXON_WATCH_WORKSPACE_AGENTS_FILE": str(agents_file),
                    "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": str(tempdir),
                },
                clear=False,
            ):
                roster = self.client.get("/api/workspaces/workspace_sched_demo/company")
                self.assertEqual(200, roster.status_code)
                employee_id = roster.json()["company"]["employees"][0]["employee_id"]

                response = self.client.patch(
                    f"/api/workspaces/workspace_sched_demo/company/employees/{employee_id}",
                    json={"enabled": False},
                )
                self.assertEqual(200, response.status_code)
                payload = response.json()
                self.assertEqual("workspace_sched_demo", payload["workspace_id"])
                self.assertEqual("frontend", payload["role"])
                self.assertFalse(payload["enabled"])
                self.assertEqual(
                    "workspace_sched_demo:frontend",
                    payload["key"],
                )
                by_role = {
                    row["role"]: row
                    for row in payload["company"]["employees"]
                }
                self.assertFalse(by_role["frontend"]["enabled"])

                scheduler = self.client.get("/api/worker-scheduler")
                self.assertEqual(
                    {"workspace_sched_demo:frontend": False},
                    scheduler.json()["employee_enabled"],
                )


if __name__ == "__main__":
    unittest.main()
