from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import task_store  # noqa: E402
from app.workspace_agents.task_duplicate_cleanup import (  # noqa: E402
    cancel_waiting_duplicates_of_completed_task,
    reconcile_workspace_waiting_duplicates,
)


class TaskDuplicateCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        db_path = str(Path(self._tmpdir.name) / "tasks.sqlite3")
        self._prev = os.environ.get("AXON_WATCH_CONTROL_PLANE_DB")
        os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = db_path
        self.addCleanup(self._restore_db_env)

    def _restore_db_env(self) -> None:
        if self._prev is None:
            os.environ.pop("AXON_WATCH_CONTROL_PLANE_DB", None)
        else:
            os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = self._prev

    def test_completion_cancels_same_role_waiting_clone(self) -> None:
        done = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Watcher: address signals/health/alerts for DashPro sentry critical",
            owner_role="watcher",
        )
        twin = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Watcher: address signals/health/alerts for DashPro sentry critical again",
            owner_role="watcher",
        )
        distinct = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Frontend: polish graduation dashboard cards for parents",
            owner_role="frontend",
        )
        completed = task_store.complete_task(done["task_id"])
        cancelled = cancel_waiting_duplicates_of_completed_task(completed)
        cancelled_ids = {row["task_id"] for row in cancelled}
        self.assertIn(twin["task_id"], cancelled_ids)
        self.assertNotIn(distinct["task_id"], cancelled_ids)
        self.assertEqual("cancelled", task_store.get_task(twin["task_id"])["status"])
        self.assertEqual("open", task_store.get_task(distinct["task_id"])["status"])

    def test_does_not_cancel_lead_follow_up_after_specialist_complete(self) -> None:
        done = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Integrations: land canary path on development then publish",
            owner_role="integrations",
        )
        follow = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal=(
                "Lead follow-up after Soren (integrations): Choose the canary path "
                "land intended app changes on clean development, then re-dispatch"
            ),
            owner_role="lead",
        )
        completed = task_store.complete_task(done["task_id"])
        cancelled = cancel_waiting_duplicates_of_completed_task(completed)
        self.assertEqual([], cancelled)
        self.assertEqual("open", task_store.get_task(follow["task_id"])["status"])

    def test_reconcile_collapses_open_twins_and_done_clones(self) -> None:
        older = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="CI repair: Security Scan failed on feat/self-hosted-ci-runner",
            owner_role="backend",
        )
        newer = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="CI repair: Security Scan failed on feat/self-hosted-ci-runner (retry)",
            owner_role="backend",
        )
        finished = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Watcher: address signals/health/alerts Gate 6 acceptance evidence",
            owner_role="watcher",
        )
        leftover = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Watcher: address signals/health/alerts Gate 6 acceptance evidence please",
            owner_role="watcher",
        )
        task_store.complete_task(finished["task_id"])

        result = reconcile_workspace_waiting_duplicates(workspace_id="workspace_dashpro")
        self.assertGreaterEqual(int(result["cancelled_count"]), 2)
        self.assertEqual("cancelled", task_store.get_task(leftover["task_id"])["status"])
        statuses = {
            task_store.get_task(older["task_id"])["status"],
            task_store.get_task(newer["task_id"])["status"],
        }
        self.assertEqual({"open", "cancelled"}, statuses)


if __name__ == "__main__":
    unittest.main()
