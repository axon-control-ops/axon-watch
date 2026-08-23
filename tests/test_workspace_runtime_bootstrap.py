from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import task_store  # noqa: E402
from app.workspace_agents.specialist_task_scope import (  # noqa: E402
    find_open_specialist_task,
    try_lease_open_specialist_task,
)
from app.workspace_agents.workspace_runtime_bootstrap import (  # noqa: E402
    ensure_project_contract,
    provision_workspace_runtime,
)


class WorkspaceRuntimeBootstrapTests(unittest.TestCase):
    def test_scaffolds_missing_project_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = ensure_project_contract(
                workspace_id="workspace_demo",
                project_root=root,
                display_name="Demo",
            )
            self.assertEqual("created", result["status"])
            self.assertTrue((root / "project.axon.yaml").is_file())

    def test_provision_skips_without_package_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = provision_workspace_runtime(
                "workspace_demo",
                project_root=root,
                install_npm=True,
            )
            self.assertEqual("skipped", report["npm"]["status"])


class SpecialistTaskScopeTests(unittest.TestCase):
    def test_finds_open_frontend_task(self) -> None:
        task_store.reset_store()
        created = task_store.create_task(
            workspace_id="workspace_tps",
            goal="Draft supplier response for Thapelosego quote",
            owner_role="frontend",
            allowed_paths=["website", "output", "docs"],
        )
        found = find_open_specialist_task("workspace_tps", "frontend")
        self.assertEqual(created["task_id"], found["task_id"])

    def test_leases_open_specialist_task(self) -> None:
        task_store.reset_store()
        created = task_store.create_task(
            workspace_id="workspace_tps",
            goal="Run npm test for navigation guards",
            owner_role="frontend",
            allowed_paths=["tests"],
        )
        leased = try_lease_open_specialist_task(
            workspace_id="workspace_tps",
            owner_role="frontend",
            lease_holder="agent-terminal-test",
            run_id="run_scope_test1234",
        )
        self.assertIsNotNone(leased)
        assert leased is not None
        self.assertEqual("leased", leased["status"])


if __name__ == "__main__":
    unittest.main()
