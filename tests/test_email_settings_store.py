"""Email operator settings store and API tests."""

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
# Prefer control-plane `app` over axon-watch `app` when both are importable.
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]
sys.path = [str(CONTROL_PLANE_ROOT), *[p for p in sys.path if p != str(CONTROL_PLANE_ROOT)]]

from app.main import app  # noqa: E402
from app.persistence import email_settings_store, run_store  # noqa: E402


class EmailSettingsStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        projection = Path(self._tmp.name) / "email-operator-settings.json"
        os.environ["AXON_WATCH_EMAIL_SETTINGS_FILE"] = str(projection)
        self.addCleanup(lambda: os.environ.pop("AXON_WATCH_EMAIL_SETTINGS_FILE", None))
        email_settings_store.reset_store()

    def test_upsert_account_and_projection(self) -> None:
        result = email_settings_store.upsert_account(
            {
                "workspace_id": "workspace_dashpro",
                "email_address": "ops@example.com",
                "imap": {"host": "imap.example.com", "folder": "INBOX"},
                "smtp": {"host": "smtp.example.com"},
                "monitor": {"enabled": True, "poll_seconds": 45},
            }
        )
        settings = result["settings"]
        self.assertEqual(1, len(settings["accounts"]))
        self.assertEqual("ops@example.com", settings["accounts"][0]["email_address"])
        self.assertEqual("INBOX", settings["accounts"][0]["imap"]["folder"])

        projection = json.loads(
            email_settings_store.projection_path().read_text(encoding="utf-8")
        )
        self.assertEqual(1, len(projection["accounts"]))
        self.assertIn("DashPro", projection["workspace_hint_map"])

    def test_delete_account(self) -> None:
        created = email_settings_store.upsert_account(
            {
                "workspace_id": "workspace_axon_watch",
                "email_address": "ops@example.com",
                "imap": {"host": "imap.example.com"},
                "smtp": {"host": "smtp.example.com"},
            }
        )
        account_id = created["account"]["account_id"]
        deleted = email_settings_store.delete_account(account_id)
        self.assertEqual([], deleted["settings"]["accounts"])

    def test_load_settings_hydrates_from_projection_when_db_empty(self) -> None:
        projection = email_settings_store.projection_path()
        projection.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "bridge_enabled": False,
                    "bridge_workspace_id": "5",
                    "stub_enabled": False,
                    "workspace_hint_map": {"DashPro": "workspace_dashpro"},
                    "accounts": [
                        {
                            "account_id": "acct-1",
                            "workspace_id": "workspace_dashpro",
                            "email_address": "ops@example.com",
                            "display_name": "Ops",
                            "imap": {
                                "host": "imap.example.com",
                                "port": 993,
                                "username": "ops@example.com",
                                "ssl": True,
                                "folder": "INBOX",
                                "password_ref": "vault:email:ops:imap",
                            },
                            "smtp": {
                                "host": "smtp.example.com",
                                "port": 465,
                                "username": "ops@example.com",
                                "ssl": True,
                                "starttls": False,
                                "from_email": "ops@example.com",
                                "password_ref": "vault:email:ops:smtp",
                            },
                            "monitor": {"enabled": True, "poll_seconds": 60},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        email_settings_store.reset_store()
        settings = email_settings_store.load_settings()
        self.assertEqual(1, len(settings["accounts"]))
        self.assertEqual("ops@example.com", settings["accounts"][0]["email_address"])
        self.assertFalse(settings["stub_enabled"])
        # Second load must come from DB, not re-import forever.
        again = email_settings_store.load_settings()
        self.assertEqual(1, len(again["accounts"]))


class EmailSettingsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        projection = Path(self._tmp.name) / "email-operator-settings.json"
        os.environ["AXON_WATCH_EMAIL_SETTINGS_FILE"] = str(projection)
        self.addCleanup(lambda: os.environ.pop("AXON_WATCH_EMAIL_SETTINGS_FILE", None))
        email_settings_store.reset_store()
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_get_and_patch_settings(self) -> None:
        response = self.client.get("/api/email/settings")
        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertIn("settings", body)
        self.assertFalse(body["settings"]["bridge_enabled"])

        patched = self.client.patch(
            "/api/email/settings",
            json={"bridge_enabled": True, "bridge_workspace_id": "7"},
        )
        self.assertEqual(200, patched.status_code)
        self.assertTrue(patched.json()["settings"]["bridge_enabled"])

    def test_upsert_account_without_password(self) -> None:
        response = self.client.post(
            "/api/email/accounts",
            json={
                "workspace_id": "workspace_dashpro",
                "email_address": "ops@example.com",
                "imap_host": "imap.example.com",
                "imap_port": 993,
                "imap_ssl": True,
                "imap_folder": "INBOX",
                "smtp_host": "smtp.example.com",
                "smtp_port": 465,
                "smtp_ssl": True,
                "smtp_starttls": False,
                "monitor_enabled": True,
                "poll_seconds": 60,
            },
        )
        self.assertEqual(200, response.status_code)
        accounts = response.json()["settings"]["accounts"]
        self.assertEqual(1, len(accounts))
        self.assertEqual("INBOX", accounts[0]["imap"]["folder"])

    def test_vault_unlocked_reads_is_unlocked_field(self) -> None:
        from app.routes import email_settings as email_routes

        with patch.object(
            email_routes.vault_routes,
            "get_vault_status",
            return_value={"vault": {"is_unlocked": True, "auto_unlock_enabled": True}},
        ):
            self.assertTrue(email_routes._vault_unlocked())

        with patch.object(
            email_routes.vault_routes,
            "get_vault_status",
            return_value={"vault": {"is_unlocked": False}},
        ):
            self.assertFalse(email_routes._vault_unlocked())

    def test_upsert_with_passwords_while_vault_locked_still_saves_config(self) -> None:
        from app.routes import email_settings as email_routes

        with patch.object(email_routes, "_vault_unlocked", return_value=False):
            response = self.client.post(
                "/api/email/accounts",
                json={
                    "workspace_id": "workspace_dashpro",
                    "email_address": "ops@example.com",
                    "imap_host": "imap.example.com",
                    "imap_port": 993,
                    "imap_ssl": True,
                    "imap_folder": "INBOX",
                    "smtp_host": "smtp.example.com",
                    "smtp_port": 465,
                    "smtp_ssl": True,
                    "smtp_starttls": False,
                    "monitor_enabled": True,
                    "poll_seconds": 60,
                    "password_imap": "secret",
                },
            )
        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertEqual(1, len(body["settings"]["accounts"]))
        self.assertIn("warning", body)
        self.assertIn("Vault", body["warning"])
        self.assertEqual("", body["settings"]["accounts"][0]["imap"]["password_ref"])

    def test_suggest_reply_route(self) -> None:
        response = self.client.post(
            "/api/email/suggest-reply",
            json={
                "subject": "Urgent blocker",
                "sender": "Ops <ops@example.com>",
                "text": "We cannot ship until this is fixed.",
            },
        )
        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["reply_subject"].startswith("Re:"))
        self.assertIn("reply_body", body)


if __name__ == "__main__":
    unittest.main()
