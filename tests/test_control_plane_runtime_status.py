from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402


class ControlPlaneRuntimeStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    @patch("app.routes.runtime.get_runtime_status")
    def test_runtime_status_route_returns_catalog_snapshot(self, mock_status) -> None:
        mock_status.return_value = {
            "updated_at": "2026-07-05T20:00:00Z",
            "default_runtime": "cursor_local",
            "local": [{"id": "cursor_local", "ready": True}],
            "cloud": [{"id": "cursor_cloud", "ready": False}],
        }
        response = self.client.get("/api/runtime/status")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("cursor_local", payload["default_runtime"])
        self.assertEqual(1, len(payload["local"]))
        self.assertEqual(1, len(payload["cloud"]))

    @patch("app.routes.runtime.get_runtime_mcp_tools")
    def test_runtime_mcp_tools_route_returns_registry(self, mock_tools) -> None:
        mock_tools.return_value = {
            "count": 1,
            "items": [{"id": "workspace_files.read", "mode_support": ["ask", "plan", "agent"]}],
        }
        response = self.client.get("/api/runtime/mcp-tools")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(1, payload["count"])
        self.assertEqual("workspace_files.read", payload["items"][0]["id"])

    @patch("app.routes.runtime.get_codex_runtime_status")
    def test_codex_runtime_status_route_returns_account_catalog(self, mock_status) -> None:
        mock_status.return_value = {
            "installed": True,
            "binary": "/usr/bin/codex",
            "auth": {"logged_in": True, "auth_method": "chatgpt"},
            "available_models": [{"id": "gpt-5.5", "label": "GPT-5.5"}],
            "codex_models": [],
            "catalog_source": "live",
        }
        response = self.client.get("/api/runtime/codex/status")
        self.assertEqual(200, response.status_code)
        self.assertEqual("gpt-5.5", response.json()["available_models"][0]["id"])


if __name__ == "__main__":
    unittest.main()
