from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store, task_store  # noqa: E402
from app.runs.service import create_run  # noqa: E402


class RestartReconcileTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        self.addCleanup(task_store.reset_store)

    def test_active_employee_run_with_missing_task_is_cancelled(self) -> None:
        from app.runs.restart_reconcile import reconcile_employee_runs_missing_tasks

        task = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Produce dashboard status report",
            owner_role="backend",
        )
        leased = task_store.lease_task(
            str(task["task_id"]),
            lease_holder="employee-workspace_dashpro-backend",
        )
        run = create_run(
            workspace_id="workspace_dashpro",
            mode="agent",
            summary="Marco: backend report",
            employee_role="backend",
            task_id=str(leased["task_id"]),
            require_leased_task=True,
        )
        task_store.reset_store()

        reconciled = reconcile_employee_runs_missing_tasks()

        self.assertEqual([str(run["run_id"])], reconciled)
        updated = run_store.get_run(str(run["run_id"]))
        assert updated is not None
        self.assertEqual("cancelled", updated.get("phase"))
        history = run_store.list_history(str(updated.get("history_ref") or ""))
        self.assertTrue(
            any(
                (item.get("receipt") or {}).get("type") == "task_ledger_reconcile"
                for item in history
            )
        )

    def test_missing_task_reconcile_can_be_scoped_to_one_employee_role(self) -> None:
        from app.runs.restart_reconcile import reconcile_employee_runs_missing_tasks

        backend = create_run(
            workspace_id="workspace_dashpro",
            mode="agent",
            summary="Marco: backend report",
            employee_role="backend",
        )
        frontend = create_run(
            workspace_id="workspace_dashpro",
            mode="agent",
            summary="Priya: frontend report",
            employee_role="frontend",
        )
        backend["task_id"] = "task_missing_backend"
        frontend["task_id"] = "task_missing_frontend"
        run_store.save_run(backend)
        run_store.save_run(frontend)

        reconciled = reconcile_employee_runs_missing_tasks(
            workspace_id="workspace_dashpro",
            employee_role="backend",
        )

        self.assertEqual([str(backend["run_id"])], reconciled)
        self.assertEqual(
            "cancelled",
            run_store.get_run(str(backend["run_id"]))["phase"],  # type: ignore[index]
        )
        self.assertEqual(
            "executing",
            run_store.get_run(str(frontend["run_id"]))["phase"],  # type: ignore[index]
        )


if __name__ == "__main__":
    unittest.main()
