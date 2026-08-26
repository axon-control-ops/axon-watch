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
from app.operator_fleet_health import build_operator_fleet_health  # noqa: E402
from app.persistence import run_store  # noqa: E402


class OperatorFleetHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_fleet_health_endpoint_returns_workspace_rows(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_axon_watch",
                "mode": "agent",
                "summary": "git status",
            },
        ).json()
        self.client.post(f"/api/runs/{created['run_id']}/review-ready")

        with patch(
            "app.operator_fleet_health.assemble_runtime_summary",
            return_value={
                "generated_at": "2026-07-07T20:00:00Z",
                "watch": {"connected": True},
                "connectors": {
                    "configured": 2,
                    "ok": 2,
                    "degraded": 0,
                    "unavailable": 0,
                    "required_unavailable": 0,
                },
                "degraded": {"active": False, "reasons": []},
            },
        ), patch(
            "app.operator_fleet_health.build_inbox_response",
            return_value={"items": [], "count": 0, "updated_at": "2026-07-07T20:00:00Z"},
        ):
            response = self.client.get("/api/operator/fleet-health")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertIn("items", payload)
        self.assertGreater(payload["count"], 0)
        axon_watch = next(
            item
            for item in payload["items"]
            if item["workspace_id"] == "workspace_axon_watch"
        )
        self.assertEqual(1, axon_watch["review_ready_count"])
        self.assertEqual("attention", axon_watch["health"])

    def test_fleet_health_ignores_background_employee_executing_runs(self) -> None:
        self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_axon_watch",
                "mode": "agent",
                "summary": "Control Plane: continuous worker shift",
                "employee_role": "backend",
            },
        )

        with patch(
            "app.operator_fleet_health.assemble_runtime_summary",
            return_value={
                "generated_at": "2026-07-07T20:00:00Z",
                "watch": {"connected": True},
                "connectors": {
                    "configured": 2,
                    "ok": 2,
                    "degraded": 0,
                    "unavailable": 0,
                    "required_unavailable": 0,
                },
                "degraded": {"active": False, "reasons": []},
            },
        ), patch(
            "app.operator_fleet_health.build_inbox_response",
            return_value={"items": [], "count": 0, "updated_at": "2026-07-07T20:00:00Z"},
        ):
            response = self.client.get("/api/operator/fleet-health")

        self.assertEqual(200, response.status_code)
        axon_watch = next(
            item
            for item in response.json()["items"]
            if item["workspace_id"] == "workspace_axon_watch"
        )
        self.assertEqual(0, axon_watch["executing_count"])
        self.assertEqual(0, axon_watch["active_runs"])
        self.assertEqual("nominal", axon_watch["health"])

    def test_fleet_health_hides_demo_isolated_workspaces(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "acceptance fixture run",
            },
        ).json()
        self.client.post(f"/api/runs/{created['run_id']}/review-ready")

        with patch(
            "app.operator_fleet_health.assemble_runtime_summary",
            return_value={
                "generated_at": "2026-07-07T20:00:00Z",
                "watch": {"connected": True},
                "connectors": {
                    "configured": 2,
                    "ok": 2,
                    "degraded": 0,
                    "unavailable": 0,
                    "required_unavailable": 0,
                },
                "degraded": {"active": False, "reasons": []},
            },
        ), patch(
            "app.operator_fleet_health.build_inbox_response",
            return_value={"items": [], "count": 0, "updated_at": "2026-07-07T20:00:00Z"},
        ):
            response = self.client.get("/api/operator/fleet-health")

        self.assertEqual(200, response.status_code)
        workspace_ids = {
            str(item.get("workspace_id", ""))
            for item in response.json().get("items", [])
            if isinstance(item, dict)
        }
        self.assertNotIn("workspace_alpha", workspace_ids)

    def test_fleet_health_does_not_crash_when_connected_watch_inbox_disappears(self) -> None:
        with patch(
            "app.operator_fleet_health.assemble_runtime_summary",
            return_value={
                "generated_at": "2026-07-07T20:00:00Z",
                "watch": {"connected": True},
                "connectors": {
                    "configured": 2,
                    "ok": 2,
                    "degraded": 0,
                    "unavailable": 0,
                    "required_unavailable": 0,
                },
                "degraded": {"active": False, "reasons": []},
            },
        ):
            payload = build_operator_fleet_health(inbox_fetcher=lambda: None)

        self.assertTrue(payload["watch_connected"])
        self.assertIn("items", payload)
        self.assertGreater(payload["count"], 0)

    def test_briefing_workspace_scope_limits_review_ready_notice(self) -> None:
        alpha = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Git status",
            },
        ).json()
        beta = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_bootstrap",
                "mode": "agent",
                "summary": "Git status",
            },
        ).json()
        self.client.post(f"/api/runs/{alpha['run_id']}/review-ready")
        self.client.post(f"/api/runs/{beta['run_id']}/review-ready")

        with patch(
            "app.operator_briefing.assemble_runtime_summary",
            return_value={
                "generated_at": "2026-07-07T20:00:00Z",
                "control_plane": {"ready": True},
                "watch": {"connected": True},
                "approvals": {"pending_count": 0},
                "degraded": {"active": False, "reasons": []},
            },
        ), patch(
            "app.operator_briefing.build_inbox_response",
            return_value={"items": [], "count": 0, "updated_at": "2026-07-07T20:00:00Z"},
        ):
            scoped = self.client.get(
                "/api/briefing?workspace_id=workspace_alpha",
            ).json()
            fleet = self.client.get("/api/briefing").json()

        self.assertEqual("workspace", scoped["scope"]["mode"])
        self.assertEqual("workspace_alpha", scoped["scope"]["workspace_id"])
        self.assertIn("Git status", scoped["notice"])
        self.assertIn("2 runs are ready", fleet["notice"])


if __name__ == "__main__":
    unittest.main()
