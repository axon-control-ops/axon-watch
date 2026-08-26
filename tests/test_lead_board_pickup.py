from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store, task_store  # noqa: E402
from app.workspace_agents.config_loader import CompanyConfig, EmployeeConfig  # noqa: E402
from app.workspace_agents.lead_board_pickup import pickup_open_lead_board_tasks  # noqa: E402


class LeadBoardPickupTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        self.addCleanup(task_store.reset_store)

    def test_pickup_starts_open_lead_tasks(self) -> None:
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Lead board ticket under semi",
            owner_role="lead",
        )
        companies = {
            "workspace_dashpro": CompanyConfig(
                company_name="DashPro",
                employees=(
                    EmployeeConfig(name="Dana", role="lead", enabled=True, primary=True),
                ),
            ),
        }
        with patch(
            "app.workspace_agents.config_loader.load_workspace_agent_configs",
            return_value=({}, {}, companies, []),
        ), patch(
            "app.workspace_agents.operator_start_task.operator_start_task",
            return_value={
                "task": {"task_id": created["task_id"], "status": "leased"},
                "run": {"run_id": "run_lead_1", "phase": "executing"},
                "thread_id": "thread_1",
            },
        ) as start:
            started = pickup_open_lead_board_tasks(starts_bound=2)
        self.assertEqual(1, len(started))
        self.assertEqual(created["task_id"], started[0]["task_id"])
        self.assertEqual("run_lead_1", started[0]["run_id"])
        start.assert_called_once_with(str(created["task_id"]))

    def test_pickup_prefers_oldest_across_workspaces(self) -> None:
        companies = {
            "workspace_dashpro": CompanyConfig(
                company_name="DashPro",
                employees=(
                    EmployeeConfig(name="Dana", role="lead", enabled=True, primary=True),
                ),
            ),
            "workspace_young_eagles_day_care": CompanyConfig(
                company_name="Young Eagles",
                employees=(
                    EmployeeConfig(name="Imani", role="lead", enabled=True, primary=True),
                ),
            ),
        }
        older_id = "task-older-ye"
        newer_id = "task-newer-dashpro"

        def _list_tasks(*, workspace_id: str, status=None, owner_role=None, limit=100):
            del status, owner_role, limit
            if workspace_id == "workspace_dashpro":
                return [
                    {
                        "task_id": newer_id,
                        "workspace_id": "workspace_dashpro",
                        "updated_at": "2026-01-01T00:00:00Z",
                        "owner_role": "lead",
                        "status": "open",
                    }
                ]
            if workspace_id == "workspace_young_eagles_day_care":
                return [
                    {
                        "task_id": older_id,
                        "workspace_id": "workspace_young_eagles_day_care",
                        "updated_at": "2020-01-01T00:00:00Z",
                        "owner_role": "lead",
                        "status": "open",
                    }
                ]
            return []

        calls: list[str] = []

        def _start(task_id: str):
            calls.append(task_id)
            return {
                "task": {"task_id": task_id, "status": "leased"},
                "run": {"run_id": f"run_{task_id}", "phase": "executing"},
                "thread_id": None,
            }

        with patch(
            "app.workspace_agents.config_loader.load_workspace_agent_configs",
            return_value=({}, {}, companies, []),
        ), patch(
            "app.persistence.task_store.list_tasks",
            side_effect=_list_tasks,
        ), patch(
            "app.workspace_agents.operator_start_task.operator_start_task",
            side_effect=_start,
        ):
            started = pickup_open_lead_board_tasks(starts_bound=1)

        self.assertEqual(1, len(started))
        self.assertEqual(older_id, started[0]["task_id"])
        self.assertEqual([older_id], calls)
