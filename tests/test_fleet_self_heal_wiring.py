"""VAXON fleet self-heal wiring: worker prompt clause and the double-dispatch guard."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.config_loader import EmployeeConfig  # noqa: E402
from app.workspace_agents.lead_checkin_assign import (  # noqa: E402
    assign_owner_role_for_failed_shift,
)
from app.workspace_agents.worker_prompt import build_continuous_worker_prompt  # noqa: E402


class WorkerPromptFleetRepairClauseTests(unittest.TestCase):
    def test_prompt_includes_fleet_repair_clause_and_callback(self) -> None:
        employee = EmployeeConfig(name="Rowan", role="watcher", owns="runtime health")
        prompt = build_continuous_worker_prompt(
            workspace_id="workspace_axon_watch",
            employee=employee,
            task={
                "task_id": "task-vaxon",
                "goal": "VAXON fleet repair [fleetbug:sandbox_resolution:abc123]: sandbox failures.",
                "acceptance_criteria": "root-cause it",
            },
        )
        self.assertIn("VAXON fleet self-heal repair", prompt)
        self.assertIn("fleet-self-heal/report-outcome", prompt)
        self.assertIn("not this workspace's product code", prompt)

    def test_prompt_does_not_leak_fleet_repair_clause_into_unrelated_tasks(self) -> None:
        employee = EmployeeConfig(name="Reed", role="backend", owns="APIs")
        prompt = build_continuous_worker_prompt(
            workspace_id="workspace_dashpro",
            employee=employee,
            task={
                "task_id": "task-normal",
                "goal": "Fix the login button styling.",
                "acceptance_criteria": "button looks right",
            },
        )
        self.assertNotIn("VAXON fleet self-heal repair", prompt)


class DoubleDispatchGuardTests(unittest.TestCase):
    def test_fleet_infra_marker_escalates_only_instead_of_auto_dispatching(self) -> None:
        role, escalate_only = assign_owner_role_for_failed_shift(
            "backend", "Lane B agent fallback reply generated (maximum recursion depth exceeded)"
        )
        self.assertEqual("backend", role)
        self.assertTrue(
            escalate_only,
            "a fleet-infra bug must not auto-dispatch a fix into the failing workspace's own repo",
        )

    def test_normal_product_failure_still_auto_dispatches(self) -> None:
        role, escalate_only = assign_owner_role_for_failed_shift(
            "backend", "acceptance=fail · failed_checks=lint"
        )
        self.assertEqual("backend", role)
        self.assertFalse(escalate_only, "ordinary product-code failures keep the existing behavior")


if __name__ == "__main__":
    unittest.main()
