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


if __name__ == "__main__":
    unittest.main()
