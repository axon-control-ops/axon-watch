from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import task_store  # noqa: E402
from app.workspace_agents.lead_fan_out import supersede_stale_queue_for_new_lead_goal  # noqa: E402


class LeadQueueSupersedeTests(unittest.TestCase):
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

    def test_supersede_cancels_overlapping_confirm_spam(self) -> None:
        older = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal=(
                "Please confirm if we did this job "
                "'The Payments button is now hidden in the parents dashboard'"
            ),
            owner_role="frontend",
        )
        sibling = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="frontend: Confirm the parent dashboard shows a Payments entry",
            owner_role="frontend",
        )
        unrelated = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Watcher: patrol PostHog monitor only",
            owner_role="watcher",
        )

        cancelled = supersede_stale_queue_for_new_lead_goal(
            workspace_id="workspace_dashpro",
            goal=(
                "The Payments button/option is now hidden in the parents dashboard "
                "- can you please fix that"
            ),
        )
        cancelled_ids = {row["task_id"] for row in cancelled}
        self.assertIn(older["task_id"], cancelled_ids)
        self.assertIn(sibling["task_id"], cancelled_ids)
        self.assertNotIn(unrelated["task_id"], cancelled_ids)
        self.assertEqual("cancelled", task_store.get_task(older["task_id"])["status"])
        self.assertEqual("open", task_store.get_task(unrelated["task_id"])["status"])


if __name__ == "__main__":
    unittest.main()
