from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store, task_store  # noqa: E402
from app.workspace_agents.operator_start_task import (  # noqa: E402
    OperatorStartTaskError,
    operator_start_task,
)


class OperatorStartTaskTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        self.addCleanup(task_store.reset_store)

    @patch(
        "app.workspace_agents.operator_start_task._wait_for_worker_dispatch_started",
        return_value=True,
    )
    @patch("app.workspace_agents.operator_start_task._kick_queued_dispatch")
    def test_operator_start_leases_and_dispatches_exact_run(self, kick, _wait) -> None:
        kick.side_effect = lambda run_id: [
            {"run_id": run_id, "phase": "executing", "employee_role": "frontend"}
        ]
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Fix waiting ticket start",
            acceptance_criteria="task leased with executing run",
            owner_role="frontend",
        )
        result = operator_start_task(str(created["task_id"]))
        task = result["task"]
        run = result["run"]
        self.assertEqual("leased", task.get("status"))
        self.assertEqual(str(run.get("run_id") or ""), str(task.get("run_id") or ""))
        self.assertEqual("executing", str(run.get("phase") or ""))
        self.assertEqual("frontend", str(run.get("employee_role") or "").strip().lower())
        kick.assert_called_once_with(str(run.get("run_id") or ""))

    @patch(
        "app.workspace_agents.operator_start_task._kick_queued_dispatch",
        return_value=[],
    )
    def test_operator_start_reports_when_target_remains_queued(self, kick) -> None:
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="No worker capacity",
            owner_role="frontend",
        )

        with self.assertRaisesRegex(OperatorStartTaskError, "remains queued"):
            operator_start_task(str(created["task_id"]))

        stored = task_store.get_task(str(created["task_id"])) or {}
        self.assertEqual("leased", stored.get("status"))
        self.assertTrue(str(stored.get("run_id") or ""))
        kick.assert_called_once_with(str(stored.get("run_id") or ""))

    @patch(
        "app.workspace_agents.operator_start_task._wait_for_worker_dispatch_started",
        return_value=True,
    )
    @patch("app.workspace_agents.operator_start_task._kick_queued_dispatch")
    def test_operator_retry_dispatches_the_leased_task_run(self, kick, _wait) -> None:
        kick.side_effect = lambda run_id: [
            {"run_id": run_id, "phase": "executing", "employee_role": "integrations"}
        ]
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Retry queued handoff",
            owner_role="integrations",
        )
        first = operator_start_task(str(created["task_id"]))
        run_id = str(first["run"]["run_id"])
        kick.reset_mock()

        retried = operator_start_task(str(created["task_id"]))

        self.assertEqual(run_id, str(retried["run"]["run_id"]))
        self.assertEqual("executing", retried["run"]["phase"])
        kick.assert_called_once_with(run_id)

    def test_operator_start_rejects_blocked_dependencies(self) -> None:
        blocker = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Blocker",
            owner_role="backend",
        )
        blocked = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Blocked child",
            owner_role="frontend",
            dependencies=[str(blocker["task_id"])],
        )
        with self.assertRaisesRegex(OperatorStartTaskError, "blocked"):
            operator_start_task(str(blocked["task_id"]))

    @patch("app.workspace_agents.operator_start_task.task_store.get_task")
    def test_operator_start_rejects_open_task_with_exhausted_attempt_budget(
        self, get_task
    ) -> None:
        get_task.return_value = {
            "task_id": "task_stale",
            "workspace_id": "workspace_young_eagles_day_care",
            "owner_role": "lead",
            "status": "open",
            "attempt_budget": 2,
            "attempts_used": 2,
            "dependencies": [],
        }

        with self.assertRaisesRegex(OperatorStartTaskError, "attempt budget is exhausted"):
            operator_start_task("task_stale")

    @patch(
        "app.workspace_agents.operator_start_task._employee_for_role",
        return_value=None,
    )
    def test_operator_start_does_not_lease_unstaffed_task(self, _employee) -> None:
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Task with no staffed owner",
            owner_role="security",
        )

        with self.assertRaisesRegex(OperatorStartTaskError, "no teammate is staffed"):
            operator_start_task(str(created["task_id"]))

        stored = task_store.get_task(str(created["task_id"]))
        self.assertEqual("open", (stored or {}).get("status"))

    @patch(
        "app.workspace_agents.operator_start_task._employee_for_role",
        return_value={
            "employee_id": "employee-disabled",
            "role": "frontend",
            "enabled": False,
        },
    )
    def test_operator_start_does_not_lease_disabled_task(self, _employee) -> None:
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Task for disabled owner",
            owner_role="frontend",
        )

        with self.assertRaisesRegex(OperatorStartTaskError, "is disabled"):
            operator_start_task(str(created["task_id"]))

        stored = task_store.get_task(str(created["task_id"]))
        self.assertEqual("open", (stored or {}).get("status"))

    @patch(
        "app.workspace_agents.operator_start_task._active_role_run",
        return_value={"run_id": "run_existing", "phase": "executing"},
    )
    def test_operator_start_does_not_duplicate_active_role_run(self, _active) -> None:
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Do not overlap Soren work",
            owner_role="integrations",
        )

        with self.assertRaisesRegex(OperatorStartTaskError, "already has active run"):
            operator_start_task(str(created["task_id"]))

        stored = task_store.get_task(str(created["task_id"])) or {}
        self.assertEqual("open", stored.get("status"))
        self.assertEqual(0, stored.get("attempts_used"))

    @patch(
        "app.workspace_agents.operator_start_task.worker_scheduler_settings_store.is_employee_enabled",
        return_value=False,
    )
    @patch(
        "app.workspace_agents.operator_start_task._employee_for_role",
        return_value={
            "employee_id": "employee-frontend",
            "role": "frontend",
            "enabled": True,
        },
    )
    def test_operator_start_respects_fleet_pause(self, _employee, _enabled) -> None:
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Paused worker must remain waiting",
            owner_role="frontend",
        )

        with self.assertRaisesRegex(OperatorStartTaskError, "paused in Fleet controls"):
            operator_start_task(str(created["task_id"]))

        stored = task_store.get_task(str(created["task_id"])) or {}
        self.assertEqual("open", stored.get("status"))


    @patch(
        "app.workspace_agents.operator_start_task._wait_for_worker_dispatch_started",
        return_value=False,
    )
    @patch("app.workspace_agents.operator_start_task._kick_queued_dispatch")
    def test_operator_start_reopens_task_when_dispatch_never_starts(self, kick, _wait) -> None:
        kick.side_effect = lambda run_id: [
            {"run_id": run_id, "phase": "executing", "employee_role": "backend"}
        ]
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Verification after Marco (backend): npm test",
            owner_role="backend",
        )
        with self.assertRaisesRegex(OperatorStartTaskError, "did not start within timeout"):
            operator_start_task(str(created["task_id"]))
        stored = task_store.get_task(str(created["task_id"])) or {}
        self.assertEqual("open", stored.get("status"))


def _stored_run(
    run_id: str,
    *,
    task_id: str,
    employee_role: str = "backend",
    phase: str = "failed",
) -> dict:
    updated_at = "2026-08-13T12:01:00Z"
    return {
        "run_id": run_id,
        "workspace_id": "workspace_dashpro",
        "lane_id": "lane_b",
        "mode": "agent",
        "status": phase,
        "phase": phase,
        "summary": "backend verify failed",
        "detail": "acceptance_evidence did not pass (Gate 6)",
        "started_at": "2026-08-13T12:00:00Z",
        "updated_at": updated_at,
        "ended_at": updated_at,
        "can_stop": False,
        "can_resume": False,
        "can_approve": False,
        "can_review": False,
        "current_step": "",
        "history_ref": f"history_{run_id}",
        "employee_role": employee_role,
        "task_id": task_id,
    }


class OperatorStartVerificationRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        self.addCleanup(task_store.reset_store)

    @patch(
        "app.workspace_agents.operator_start_task._employee_for_role",
        return_value={
            "employee_id": "employee-marco",
            "name": "Marco",
            "role": "backend",
            "enabled": True,
        },
    )
    @patch(
        "app.workspace_agents.operator_start_task._wait_for_worker_dispatch_started",
        return_value=True,
    )
    @patch("app.workspace_agents.operator_start_task._kick_queued_dispatch")
    def test_operator_start_repairs_stale_task_id_via_verification_ticket(
        self,
        kick,
        _wait,
        _employee,
    ) -> None:
        kick.side_effect = lambda run_id: [
            {"run_id": run_id, "phase": "executing", "employee_role": "backend"}
        ]
        verify = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Verification after Marco (backend): npm test [from run run_failed]",
            owner_role="backend",
        )
        run_store.save_run(_stored_run("run_failed", task_id="task-vanished"))

        result = operator_start_task("task-vanished")

        self.assertEqual(str(verify["task_id"]), str(result["task"]["task_id"]))
        self.assertEqual("executing", str(result["run"]["phase"]))

    @patch(
        "app.workspace_agents.operator_start_task._employee_for_role",
        return_value={
            "employee_id": "employee-marco",
            "name": "Marco",
            "role": "backend",
            "enabled": True,
        },
    )
    @patch(
        "app.workspace_agents.operator_start_task._post_assignment_to_employee_thread",
        return_value="thread_marco",
    )
    @patch(
        "app.workspace_agents.operator_start_task._wait_for_worker_dispatch_started",
        return_value=True,
    )
    @patch("app.workspace_agents.operator_start_task._kick_queued_dispatch")
    def test_operator_start_reopens_leased_task_after_failed_run(
        self,
        kick,
        _wait,
        _thread,
        _employee,
    ) -> None:
        kick.side_effect = lambda run_id: [
            {"run_id": run_id, "phase": "executing", "employee_role": "backend"}
        ]
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Verification after Marco (backend): npm test",
            owner_role="backend",
        )
        run_store.save_run(
            _stored_run("run_failed_verify", task_id=str(created["task_id"]))
        )
        leased = task_store.lease_task(
            str(created["task_id"]),
            lease_holder="operator-start-workspace_dashpro-backend",
            run_id="run_failed_verify",
        )
        self.assertEqual("leased", leased.get("status"))

        result = operator_start_task(str(created["task_id"]))

        self.assertEqual("executing", str(result["run"]["phase"]))
        stored = task_store.get_task(str(created["task_id"])) or {}
        self.assertEqual("leased", stored.get("status"))
        self.assertNotEqual("run_failed_verify", str(stored.get("run_id") or ""))


if __name__ == "__main__":
    unittest.main()
