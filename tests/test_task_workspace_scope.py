"""Cross-workspace mutation routing guard tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_app_loader import prepare_control_plane_imports
from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


class TaskWorkspaceScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = prepare_control_plane_imports()
        self.addCleanup(self._restore)
        from app.persistence import chat_store, run_store, task_store

        isolate_control_plane_db(self, run_store)
        chat_store.reset_store()
        task_store.reset_store()

    def _restore(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.modules.update(self._saved)

    def test_rejects_control_plane_mutation_before_creating_product_task(self) -> None:
        from app.persistence import task_store
        from app.workspace_agents.lead_fan_out import LeadFanOutError, materialize_lead_fan_out

        with self.assertRaisesRegex(LeadFanOutError, "workspace_axon_watch"):
            materialize_lead_fan_out(
                workspace_id="workspace_dashpro",
                goal="Fix the control-plane scoped-task gate before deployment",
            )
        self.assertEqual([], task_store.list_tasks(workspace_id="workspace_dashpro"))

    def test_allows_read_only_control_plane_health_check(self) -> None:
        from app.workspace_agents.task_workspace_scope import cross_workspace_mutation_blocker

        self.assertIsNone(cross_workspace_mutation_blocker(
            workspace_id="workspace_dashpro",
            goal="Check control-plane health and report the current status",
        ))


if __name__ == "__main__":
    unittest.main()
