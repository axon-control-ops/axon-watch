from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402


class ControlPlaneWorkspacesTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_workspaces_index_returns_defaults_and_run_workspace(self) -> None:
        self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_gamma",
                "mode": "agent",
                "summary": "Workspace discovery run",
            },
        )

        response = self.client.get("/api/workspaces")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        ids = {item["workspace_id"] for item in payload["items"]}

        self.assertIn("workspace_alpha", ids)
        self.assertIn("workspace_bootstrap", ids)
        self.assertIn("workspace_smoke", ids)
        self.assertIn("workspace_gamma", ids)

    def test_workspaces_operator_scope_hides_demo_defaults(self) -> None:
        response = self.client.get("/api/workspaces?scope=operator")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        ids = {item["workspace_id"] for item in payload["items"]}
        self.assertEqual("operator", payload["scope"])
        self.assertNotIn("workspace_smoke", ids)
        self.assertNotIn("workspace_bootstrap", ids)
        self.assertNotIn("workspace_alpha", ids)

    def test_workspaces_show_returns_known_workspace(self) -> None:
        response = self.client.get("/api/workspaces/workspace_alpha")
        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertEqual("workspace_alpha", body["workspace_id"])
        self.assertEqual("isolated_root", body["connection_kind"])
        # workspace_alpha has no configured company (config/workspace-agents.json)
        self.assertFalse(body["has_active_team"])

    def test_workspaces_show_returns_404_for_unknown_workspace(self) -> None:
        response = self.client.get("/api/workspaces/workspace_missing")
        self.assertEqual(404, response.status_code)

    def test_workspaces_index_includes_project_bound_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            project_root = Path(tempdir) / "bound-project"
            project_root.mkdir()
            bindings_file = Path(tempdir) / "bindings.json"
            bindings_file.write_text(
                json.dumps(
                    {
                        "bindings": {
                            "workspace_bound_demo": {
                                "project_root": str(project_root),
                                "display_name": "Bound demo",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "AXON_WATCH_WORKSPACE_BINDINGS_FILE": str(bindings_file),
                    "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": str(tempdir),
                },
                clear=False,
            ):
                response = self.client.get("/api/workspaces")

        self.assertEqual(200, response.status_code)
        by_id = {item["workspace_id"]: item for item in response.json()["items"]}
        self.assertIn("workspace_bound_demo", by_id)
        record = by_id["workspace_bound_demo"]
        self.assertEqual("project_path", record["connection_kind"])
        self.assertEqual(str(project_root.resolve()), record["project_root"])
        self.assertEqual("Bound demo", record["display_name"])


if __name__ == "__main__":
    unittest.main()
