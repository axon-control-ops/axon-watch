from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402


class ControlPlaneVaultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    @patch("app.vault.watch_adapter.fetch_watch_vault_snapshot")
    def test_vault_status_route_returns_watch_snapshot(self, mock_snapshot) -> None:
        mock_snapshot.return_value = {
            "is_setup": True,
            "is_unlocked": False,
            "ttl_remaining": 0,
            "auto_unlock_enabled": False,
            "import_file_present": False,
            "import_file": "/tmp/vault-import.json",
            "available_keys": [],
            "sources": ["process_env"],
            "consumers": [],
            "known_keys": ["SENTRY_AUTH_TOKEN"],
        }
        response = self.client.get("/api/vault/status")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual([], payload["vault"]["available_keys"])
        self.assertEqual(["SENTRY_AUTH_TOKEN"], payload["vault"]["known_keys"])
        self.assertFalse(payload["vault"]["is_unlocked"])

    @patch("app.vault.watch_adapter.fetch_watch_vault_snapshot")
    @patch("app.vault.watch_adapter.post_watch_vault_monitor_import")
    def test_vault_import_monitor_keys_route_returns_import_result_and_refreshed_snapshot(
        self,
        mock_import,
        mock_snapshot,
    ) -> None:
        mock_import.return_value = {"imported_keys": ["SENTRY_AUTH_TOKEN"], "count": 1}
        mock_snapshot.return_value = {
            "is_setup": True,
            "is_unlocked": True,
            "import_file_present": True,
            "import_file": "/tmp/vault-import.json",
            "available_keys": ["SENTRY_AUTH_TOKEN"],
            "sources": ["process_env", "vault_import"],
            "consumers": [],
        }
        response = self.client.post(
            "/api/vault/import/monitor-keys",
            json={"secrets": {"SENTRY_AUTH_TOKEN": "abc123"}},
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(1, payload["vault_import"]["count"])
        self.assertIn("SENTRY_AUTH_TOKEN", payload["vault"]["available_keys"])


if __name__ == "__main__":
    unittest.main()
