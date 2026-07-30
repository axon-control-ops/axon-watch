from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import task_store  # noqa: E402
from app.workspace_agents.operator_start_task import (  # noqa: E402
    OperatorStartTaskError,
    operator_start_task,
)


class OperatorStartTaskTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        db_path = str(Path(self._tmpdir.name) / "control.sqlite3")
        self._prev = os.environ.get("AXON_WATCH_CONTROL_PLANE_DB")
        os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = db_path
        self.addCleanup(self._restore_db_env)
        task_store.reset_store()

    def _restore_db_env(self) -> None:
        if self._prev is None:
            os.environ.pop("AXON_WATCH_CONTROL_PLANE_DB", None)
        else:
            os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = self._prev

    def test_operator_start_leases_open_task_and_queues_run(self) -> None:
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Fix waiting ticket start",
            acceptance_criteria="task leased with queued run",
            owner_role="frontend",
        )
        result = operator_start_task(str(created["task_id"]))
        task = result["task"]
        run = result["run"]
        self.assertEqual("leased", task.get("status"))
        self.assertEqual(str(run.get("run_id") or ""), str(task.get("run_id") or ""))
        # Operator Start kicks Lane B immediately so Manual mode does not leave QUEUED.
        self.assertIn(
            str(run.get("phase") or ""),
            {"queued", "starting", "planning", "executing"},
        )
        self.assertEqual("frontend", str(run.get("employee_role") or "").strip().lower())

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


if __name__ == "__main__":
    unittest.main()
