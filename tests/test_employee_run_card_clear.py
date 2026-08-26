"""Clearing an agent card hides stale outcomes without deleting evidence."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store  # noqa: E402
from app.runs.employee_dismissal import dismiss_employee_role_runs  # noqa: E402
from app.runs.service import create_run, fail_run  # noqa: E402
from app.workspace_agents.run_outcome import latest_role_run_outcome  # noqa: E402


class EmployeeRunCardClearTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_dismissed_employee_run_no_longer_drives_roster_outcome(self) -> None:
        created = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Backend: continuous worker shift",
            employee_role="backend",
        )
        fail_run(
            created["run_id"],
            receipt_summary="implementation requested but worker produced no changed files",
        )
        self.assertIsNotNone(latest_role_run_outcome("workspace_axon_watch", "backend"))

        dismissed = dismiss_employee_role_runs(
            workspace_id="workspace_axon_watch",
            role="backend",
        )

        self.assertEqual([created["run_id"]], dismissed)
        self.assertIsNone(latest_role_run_outcome("workspace_axon_watch", "backend"))
        stored = run_store.get_run(created["run_id"])
        assert stored is not None
        self.assertEqual("failed", stored["phase"])
        self.assertEqual("operator cleared agent card", stored["dismiss_reason"])
        self.assertTrue(
            any(
                item.get("receipt", {}).get("type") == "operator_clear_agent_card"
                for item in run_store.list_history(stored["history_ref"])
            )
        )


if __name__ == "__main__":
    unittest.main()
