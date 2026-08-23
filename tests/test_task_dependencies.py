"""Tests for shared task dependency checks."""

from __future__ import annotations

import unittest

from app.persistence import task_store  # noqa: E402
from app.workspace_agents.task_dependencies import (  # noqa: E402
    dependencies_completed,
    dependency_blocker_message,
)


class TaskDependenciesTests(unittest.TestCase):
    def test_cancelled_dependency_still_blocks(self) -> None:
        cancelled = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Verification after Marco backend work",
            owner_role="backend",
        )
        task_store.cancel_task(str(cancelled["task_id"]))
        blocked = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Lead follow-up",
            owner_role="lead",
            dependencies=[str(cancelled["task_id"])],
        )
        self.assertFalse(dependencies_completed(blocked))
        message = dependency_blocker_message(blocked)
        self.assertIn("backend", message)
        self.assertIn("cancelled", message)

    def test_completed_dependency_unblocks(self) -> None:
        done = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Done",
            owner_role="backend",
        )
        task_store.complete_task(str(done["task_id"]))
        child = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Child",
            owner_role="lead",
            dependencies=[str(done["task_id"])],
        )
        self.assertTrue(dependencies_completed(child))


class RefreshTaskDependenciesTests(unittest.TestCase):
    def test_refresh_replaces_dependency_list_on_open_task(self) -> None:
        stale = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Stale verification",
            owner_role="backend",
        )
        task_store.cancel_task(str(stale["task_id"]))
        fresh = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Fresh verification",
            owner_role="backend",
        )
        lead = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Lead follow-up",
            owner_role="lead",
            dependencies=[str(stale["task_id"])],
        )
        updated = task_store.refresh_task_dependencies(
            str(lead["task_id"]),
            [str(fresh["task_id"])],
        )
        self.assertEqual([str(fresh["task_id"])], updated.get("dependencies"))


if __name__ == "__main__":
    unittest.main()
