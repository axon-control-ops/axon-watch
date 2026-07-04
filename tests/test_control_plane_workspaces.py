from __future__ import annotations

import sys
import unittest
from pathlib import Path

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

    def test_workspaces_show_returns_known_workspace(self) -> None:
        response = self.client.get("/api/workspaces/workspace_alpha")
        self.assertEqual(200, response.status_code)
        self.assertEqual({"workspace_id": "workspace_alpha"}, response.json())

    def test_workspaces_show_returns_404_for_unknown_workspace(self) -> None:
        response = self.client.get("/api/workspaces/workspace_missing")
        self.assertEqual(404, response.status_code)


if __name__ == "__main__":
    unittest.main()
