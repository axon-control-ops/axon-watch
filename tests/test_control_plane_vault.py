from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402


class _FakeSentryResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return b'[{"slug":"edudashpro"}]'


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

    @patch("app.vault.sentry_validation.post_watch_sentry_probe_write")
    @patch("app.vault.sentry_validation.sentry_urlopen")
    @patch("app.vault.sentry_validation.get_vault_secret")
    @patch("app.vault.sentry_validation.list_vault_secrets")
    def test_vault_validate_sentry_route_returns_sanitized_health(
        self,
        mock_list,
        mock_get,
        mock_urlopen,
        mock_write_probe,
    ) -> None:
        mock_list.return_value = [
            {"id": 1, "name": "SENTRY_AUTH_TOKEN"},
            {"id": 2, "name": "SENTRY_ORG_SLUG"},
            {"id": 3, "name": "SENTRY_PROJECT_SLUG"},
        ]
        mock_get.side_effect = [
            {"password": "sntryu_test_token_value"},
            {"password": "edudash-pro"},
            {"password": "edudashpro"},
        ]
        mock_urlopen.return_value = _FakeSentryResponse()
        mock_write_probe.return_value = {
            "ok": True,
            "write_scope": True,
            "detail": "write probe ok",
        }

        response = self.client.post("/api/vault/validate/sentry")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["read_ok"])
        self.assertTrue(payload["project_found"])
        self.assertTrue(payload["write_ok"])
        self.assertEqual("sntryu…", payload["token_prefix"])
        self.assertNotIn("sntryu_test_token_value", str(payload))

    @patch("app.vault.sentry_validation.get_vault_secret")
    @patch("app.vault.sentry_validation.list_vault_secrets")
    def test_vault_validate_sentry_route_reports_missing_keys(self, mock_list, mock_get) -> None:
        mock_list.return_value = [{"id": 1, "name": "SENTRY_AUTH_TOKEN"}]
        mock_get.return_value = {"password": "sntryu_test_token_value"}

        response = self.client.post("/api/vault/validate/sentry")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertFalse(payload["present"])
        self.assertIn("SENTRY_ORG_SLUG", payload["detail"])


if __name__ == "__main__":
    unittest.main()
