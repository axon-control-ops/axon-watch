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


class ControlPlaneOperatorBriefingTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_briefing_endpoint_returns_canonical_shape(self) -> None:
        with patch(
            "app.operator_briefing.build_inbox_response",
            return_value={
                "items": [
                    {
                        "signal_id": "signal_watch_bootstrap_ready",
                        "workspace_id": "workspace_bootstrap",
                        "title": "Watch bootstrap ready",
                        "summary": "Watch bootstrap signal is available.",
                        "severity": "info",
                        "status": "open",
                        "source": "watch",
                        "updated_at": "2026-07-04T08:00:00Z",
                        "action_type": "open_dashboard",
                    }
                ],
                "count": 1,
                "updated_at": "2026-07-04T08:00:00Z",
            },
        ), patch(
            "app.operator_briefing.assemble_runtime_summary",
            return_value={
                "generated_at": "2026-07-04T08:00:00Z",
                "control_plane": {"ready": True},
                "watch": {"connected": True},
                "approvals": {"pending_count": 0},
                "degraded": {"active": False, "reasons": []},
            },
        ):
            response = self.client.get("/api/briefing")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(
            {
                "generated_at",
                "scope",
                "notice",
                "advise",
                "executive_rhythm",
                "top_signals",
                "pending_approvals",
                "active_runs",
                "next_safe_actions",
                "degraded",
                "connectivity",
                "memory_highlights",
                "due_reminders",
                "host_artifacts",
                "operator_presence",
                "cli_runtime",
            },
            set(payload),
        )
        self.assertEqual(1, len(payload["top_signals"]))
        self.assertEqual(0, payload["pending_approvals"]["count"])
        self.assertTrue(payload["connectivity"]["control_plane_ready"])
        self.assertTrue(payload["connectivity"]["watch_connected"])
        self.assertIn("persona_voice_line", payload["operator_presence"])
        self.assertIn("spoken_alert", payload["operator_presence"])

    def test_briefing_includes_resume_action_for_paused_run(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Paused run",
                "detail": "Ready to resume",
            },
        ).json()
        self.client.post(f"/api/runs/{created['run_id']}/stop")

        response = self.client.get("/api/briefing")
        self.assertEqual(200, response.status_code)
        payload = response.json()

        self.assertEqual("paused", payload["active_runs"][0]["phase"])
        self.assertEqual("resume_run", payload["next_safe_actions"][0]["kind"])
        self.assertEqual(created["run_id"], payload["next_safe_actions"][0]["run_id"])

    def test_briefing_includes_pending_approval_projection(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Approval-bound run",
                "detail": "Awaiting explicit approval",
                "requires_approval": True,
            },
        ).json()

        response = self.client.get("/api/briefing")
        self.assertEqual(200, response.status_code)
        payload = response.json()

        self.assertEqual(1, payload["pending_approvals"]["count"])
        self.assertEqual("awaiting_approval", payload["active_runs"][0]["phase"])
        self.assertEqual(f"approval_{created['run_id']}", payload["pending_approvals"]["items"][0]["approval_id"])
        self.assertEqual("approve_run", payload["next_safe_actions"][0]["kind"])
        self.assertEqual(created["run_id"], payload["next_safe_actions"][0]["run_id"])
        self.assertIn("approval", payload["notice"])
        self.assertIn("Approve", payload["advise"])

    def test_briefing_omits_top_signals_when_watch_disconnected(self) -> None:
        with patch(
            "app.operator_briefing.assemble_runtime_summary",
            return_value={
                "generated_at": "2026-07-04T08:00:00Z",
                "control_plane": {"ready": True},
                "watch": {"connected": False},
                "approvals": {"pending_count": 0},
                "degraded": {"active": True, "reasons": ["watch probe failed"]},
                "signals": {"top_items": [], "open_count": 0},
            },
        ), patch(
            "app.operator_briefing.build_inbox_response",
            return_value={
                "items": [
                    {
                        "signal_id": "signal_should_not_surface",
                        "workspace_id": "workspace_alpha",
                        "title": "Hidden when degraded",
                        "summary": "Must not appear",
                        "severity": "info",
                        "status": "open",
                        "source": "watch",
                        "updated_at": "2026-07-04T08:00:00Z",
                        "action_type": "none",
                    }
                ],
                "count": 1,
                "updated_at": "2026-07-04T08:00:00Z",
            },
        ) as inbox_mock, patch(
            "app.operator_briefing.list_operator_facing_active_runs",
            return_value=[],
        ):
            response = self.client.get("/api/briefing")

        payload = response.json()
        self.assertEqual(0, len(payload["top_signals"]))
        inbox_mock.assert_not_called()

    def test_briefing_surfaces_degraded_runtime_action(self) -> None:
        with patch(
            "app.operator_briefing.assemble_runtime_summary",
            return_value={
                "generated_at": "2026-07-04T08:00:00Z",
                "control_plane": {"ready": True},
                "watch": {"connected": False},
                "approvals": {"pending_count": 0},
                "degraded": {"active": True, "reasons": ["watch probe failed"]},
            },
        ), patch(
            "app.operator_briefing.build_inbox_response",
            return_value={"items": [], "count": 0, "updated_at": ""},
        ), patch(
            "app.operator_briefing.list_operator_facing_active_runs",
            return_value=[],
        ):
            response = self.client.get("/api/briefing")

        payload = response.json()
        self.assertFalse(payload["connectivity"]["watch_connected"])
        self.assertTrue(payload["degraded"]["active"])
        self.assertEqual("inspect_runtime", payload["next_safe_actions"][0]["kind"])

    def test_briefing_advise_redirects_when_focused_workspace_is_quiet(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_dashpro",
                "mode": "agent",
                "summary": "Hot guarded run",
                "detail": "Needs approval elsewhere",
                "requires_approval": True,
            },
        ).json()
        self.assertEqual("awaiting_approval", created["phase"])

        with patch(
            "app.operator_briefing.assemble_runtime_summary",
            return_value={
                "generated_at": "2026-07-16T12:00:00Z",
                "control_plane": {"ready": True},
                "watch": {"connected": True},
                "approvals": {"pending_count": 1},
                "degraded": {"active": False, "reasons": []},
                "cli_runtime": {"dispatch_ready": True},
            },
        ), patch(
            "app.operator_briefing.build_inbox_response",
            return_value={"items": [], "count": 0, "updated_at": "2026-07-16T12:00:00Z"},
        ):
            quiet = self.client.get("/api/briefing?workspace_id=workspace_alpha")
            fleet = self.client.get("/api/briefing")

        quiet_payload = quiet.json()
        self.assertEqual(200, quiet.status_code)
        self.assertEqual("workspace", quiet_payload["scope"]["mode"])
        self.assertEqual(0, quiet_payload["pending_approvals"]["count"])
        self.assertEqual("", quiet_payload["notice"])
        self.assertIn("Approve the guarded run", quiet_payload["advise"])
        self.assertRegex(quiet_payload["advise"], r"(?i)dashpro")
        self.assertIn("before starting more", quiet_payload["advise"])

        fleet_payload = fleet.json()
        self.assertEqual(200, fleet.status_code)
        self.assertEqual("fleet", fleet_payload["scope"]["mode"])
        self.assertIn("Approve the guarded run", fleet_payload["advise"])
        self.assertRegex(fleet_payload["advise"], r"(?i)dashpro")

    def test_briefing_omits_background_employee_runs_from_active_projection(self) -> None:
        self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Control Plane: continuous worker shift",
                "employee_role": "backend",
            },
        )

        with patch(
            "app.operator_briefing.assemble_runtime_summary",
            return_value={
                "generated_at": "2026-07-04T08:00:00Z",
                "control_plane": {"ready": True},
                "watch": {"connected": True},
                "approvals": {"pending_count": 0},
                "degraded": {"active": False, "reasons": []},
            },
        ), patch(
            "app.operator_briefing.build_inbox_response",
            return_value={"items": [], "count": 0, "updated_at": "2026-07-04T08:00:00Z"},
        ):
            response = self.client.get("/api/briefing")

        self.assertEqual(200, response.status_code)
        payload = response.json()

        self.assertEqual([], payload["active_runs"])
        self.assertEqual("", payload["notice"])


if __name__ == "__main__":
    unittest.main()
