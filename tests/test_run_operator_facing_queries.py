"""Operator-facing active run query helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402
from app.runs.queries import (  # noqa: E402
    is_background_employee_run,
    list_active_runs,
    list_operator_facing_active_runs,
    list_operator_facing_runs,
)
from app.runs.service import create_run  # noqa: E402
from app.workspace_agents.status import derive_agent_status  # noqa: E402
from tests.support.control_plane_db import isolate_control_plane_db  # noqa: E402


class RunOperatorFacingQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_background_employee_run_detection(self) -> None:
        tagged = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: continuous worker shift",
            employee_role="backend",
        )
        untagged = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Operator git status",
        )

        self.assertTrue(is_background_employee_run(tagged))
        self.assertFalse(is_background_employee_run(untagged))

    def test_operator_facing_active_runs_exclude_role_tagged_shifts(self) -> None:
        tagged = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: continuous worker shift",
            employee_role="backend",
        )
        untagged = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Operator git status",
        )

        active = list_active_runs()
        operator_facing = list_operator_facing_active_runs()

        self.assertEqual(2, len(active))
        self.assertEqual(1, len(operator_facing))
        self.assertEqual(str(untagged["run_id"]), operator_facing[0]["run_id"])
        self.assertNotEqual(str(tagged["run_id"]), operator_facing[0]["run_id"])

    def test_operator_facing_runs_exclude_role_tagged_shifts_including_terminal(self) -> None:
        tagged = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: continuous worker shift",
            employee_role="backend",
        )
        untagged = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Operator git status",
        )

        operator_facing = list_operator_facing_runs()
        run_ids = {str(run["run_id"]) for run in operator_facing}

        self.assertIn(str(untagged["run_id"]), run_ids)
        self.assertNotIn(str(tagged["run_id"]), run_ids)
        self.assertEqual(1, len(operator_facing))

    def test_runs_api_operator_facing_query_excludes_background_shifts(self) -> None:
        tagged = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_axon_watch",
                "mode": "agent",
                "summary": "Control Plane: continuous worker shift",
                "employee_role": "backend",
            },
        ).json()
        untagged = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_axon_watch",
                "mode": "agent",
                "summary": "Operator git status",
            },
        ).json()

        full = self.client.get("/api/runs").json()
        operator_facing = self.client.get("/api/runs?operator_facing=true").json()

        self.assertEqual(2, full["count"])
        self.assertEqual(1, operator_facing["count"])
        self.assertEqual(untagged["run_id"], operator_facing["items"][0]["run_id"])
        self.assertNotEqual(tagged["run_id"], operator_facing["items"][0]["run_id"])

    def test_derive_agent_status_ignores_background_employee_runs(self) -> None:
        create_run(
            workspace_id="workspace_demo",
            mode="agent",
            summary="Control Plane: continuous worker shift",
            employee_role="backend",
        )
        self.assertEqual("idle", derive_agent_status("workspace_demo"))


if __name__ == "__main__":
    unittest.main()
