"""Lead dispatch-mechanism prompt cases (split from the worker prompt suite)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


class LeadDispatchMechanismTests(unittest.TestCase):
    """Every colleague must know the audited direct-assignment mechanism."""

    def _prompt(self, role: str) -> str:
        from app.workspace_agents.config_loader import EmployeeConfig
        from app.workspace_agents.worker_prompt import build_continuous_worker_prompt

        return build_continuous_worker_prompt(
            workspace_id="workspace_dashpro",
            employee=EmployeeConfig(name="Probe", role=role, owns="probe"),
            task={"task_id": "task-probe", "goal": "Route this work to the team"},
        )

    def test_lead_is_told_how_to_dispatch(self) -> None:
        prompt = self._prompt("lead")
        self.assertIn("axon-assign --workspace", prompt)
        self.assertIn("a document dispatches", prompt)

    def test_lead_is_told_not_to_fan_out_across_tenants(self) -> None:
        self.assertIn("needs operator approval", self._prompt("lead"))

    def test_specialists_can_assign_the_colleague_who_owns_a_dependency(self) -> None:
        for role in ("backend", "frontend", "integrations", "watcher"):
            with self.subTest(role=role):
                prompt = self._prompt(role)
                self.assertIn("axon-assign", prompt)
                self.assertIn("--role", prompt)
                self.assertIn("current_workspace_id", prompt)

    def test_axon_x_mobile_companion_prompt_forbids_root_dev_command(self) -> None:
        from app.workspace_agents.config_loader import EmployeeConfig
        from app.workspace_agents.worker_prompt import build_continuous_worker_prompt

        prompt = build_continuous_worker_prompt(
            workspace_id="workspace_axon_watch",
            employee=EmployeeConfig(name="Jules", role="frontend", owns="console UI"),
            task={
                "task_id": "task-mobile",
                "goal": (
                    "Axon-X mobile companion: work only on the Expo native companion "
                    "in `apps/console-mobile` for `workspace_axon_watch`."
                ),
                "acceptance_criteria": (
                    "Receipts prove Axon-X mobile companion readiness: "
                    "`npm run typecheck -w @axon-watch/console-mobile`; "
                    "`npm exec -w @axon-watch/console-mobile -- expo config --json`."
                ),
                "allowed_paths": ["apps/console-mobile", "package.json", "package-lock.json", "README.md"],
                "exclusive_paths": ["apps/console-mobile"],
            },
        )

        self.assertIn("Never run root `npm run dev`", prompt)
        self.assertIn("interpret that as `npm run dev:console-mobile`", prompt)
        self.assertIn("apps/console-mobile", prompt)
        self.assertIn("127.0.0.1", prompt)


if __name__ == "__main__":
    unittest.main()
