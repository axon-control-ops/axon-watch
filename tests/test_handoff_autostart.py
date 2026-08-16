from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import handoff_store, run_store, task_store  # noqa: E402
from app.workspace_agents.operator_start_task import OperatorStartTaskError  # noqa: E402
from app.workspace_handoff_routing import (  # noqa: E402
    route_cross_workspace_ticket,
    try_autostart_handoff_task,
)


class HandoffAutostartTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        handoff_store.reset_store()
        self.addCleanup(task_store.reset_store)
        self.addCleanup(handoff_store.reset_store)

    @patch("app.workspace_agents.operator_start_task._kick_queued_dispatch")
    @patch("app.workspace_agents.operator_start_task._wait_for_worker_dispatch_started", return_value=True)
    def test_try_autostart_calls_operator_start_under_scheduler_off(self, _wait, kick) -> None:
        kick.side_effect = lambda run_id: [
            {"run_id": run_id, "phase": "executing", "employee_role": "frontend"}
        ]
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Fix app child card avatar",
            owner_role="frontend",
        )
        # Semi sets scheduler_enabled=False; operator_start still leases + kicks.
        with patch(
            "app.workspace_agents.scheduler.scheduler_enabled",
            return_value=False,
        ):
            result = try_autostart_handoff_task(str(created["task_id"]))
        self.assertEqual("started", result.get("status"))
        self.assertTrue(str(result.get("run_id") or ""))
        kick.assert_called_once()

    def test_try_autostart_marks_queued_only_when_leased_without_slot(self) -> None:
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Queued after kick",
            owner_role="frontend",
        )
        task_id = str(created["task_id"])
        leased = task_store.lease_task(task_id, lease_holder="test-handoff-autostart")
        task_store.bind_task_run(task_id, "run_queued_1")
        self.assertEqual("leased", (task_store.get_task(task_id) or {}).get("status"))
        self.assertTrue(str(leased.get("task_id") or ""))

        with patch(
            "app.workspace_agents.operator_start_task.operator_start_task",
            side_effect=OperatorStartTaskError(
                "handoff remains queued; no worker dispatch slot is available"
            ),
        ):
            result = try_autostart_handoff_task(task_id)
        self.assertEqual("queued", result.get("status"))
        self.assertEqual("run_queued_1", result.get("run_id"))

    def test_try_autostart_soft_fails_when_capacity_blocked(self) -> None:
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Blocked by capacity",
            owner_role="frontend",
        )
        with patch(
            "app.workspace_agents.operator_start_task.operator_start_task",
            side_effect=OperatorStartTaskError(
                'teammate for role "frontend" already has active run run_busy'
            ),
        ):
            result = try_autostart_handoff_task(str(created["task_id"]))
        self.assertEqual("waiting", result.get("status"))
        stored = task_store.get_task(str(created["task_id"])) or {}
        self.assertEqual("open", stored.get("status"))

    @patch("app.workspace_handoff_routing.try_autostart_handoff_task")
    @patch("app.workspace_handoff_routing.route_teammate_decision")
    def test_route_attempts_autostart_after_task_create(
        self,
        route_decision,
        autostart,
    ) -> None:
        class _Emp:
            role = "frontend"
            employee_id = "employee-workspace_dashpro-frontend-2"
            name = "Priya"

        class _Decision:
            should_route = True
            employee = _Emp()

        route_decision.return_value = _Decision()
        autostart.return_value = {
            "status": "queued",
            "run_id": "run_queued",
            "detail": "waiting on a dispatch slot",
        }
        recorded = handoff_store.create_handoff_record(
            source_workspace_id="workspace_young_eagles_day_care",
            target_workspace_id="workspace_dashpro",
            task="Update Child card avatar layout",
            reason="App UI belongs to DashPro",
        )
        with patch(
            "app.workspace_handoff_routing._lead_employee",
            side_effect=lambda wid: {
                "employee_id": f"employee-{wid}-lead-0",
                "name": "Lead",
                "role": "lead",
            },
        ), patch(
            "app.workspace_handoff_routing.chat_store.find_thread_for_employee",
            return_value=None,
        ), patch(
            "app.workspace_handoff_routing.chat_store.create_thread",
            side_effect=lambda **kwargs: {
                "thread_id": f"thread_{kwargs.get('workspace_id')}",
            },
        ), patch(
            "app.workspace_handoff_routing.chat_store.save_message",
            return_value=None,
        ):
            updated = route_cross_workspace_ticket(recorded)

        self.assertEqual("routed", updated.get("status"))
        task_id = str(updated.get("target_task_id") or "")
        self.assertTrue(task_id.startswith("task-"))
        autostart.assert_called_once_with(task_id)
