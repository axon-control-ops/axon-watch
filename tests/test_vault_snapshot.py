from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
sys.path.insert(0, str(WATCH_ROOT))

from app.vault.credential_resolver import merge_vault_import  # noqa: E402
from app.vault.snapshot import ALLOWED_IMPORT_KEYS, vault_operator_snapshot  # noqa: E402


def _cursor_subscription_ready() -> dict[str, object]:
    return {
        "installed": True,
        "logged_in": True,
        "account_label": "operator@example.com",
        "message": "Cursor CLI subscription (operator@example.com)",
    }


def _cursor_subscription_missing() -> dict[str, object]:
    return {
        "installed": True,
        "logged_in": False,
        "account_label": "",
        "message": "Run `cursor agent login` on the host or add CURSOR_API_KEY to /vault.",
    }


class VaultSnapshotTests(unittest.TestCase):
    def test_operator_snapshot_includes_consumer_map_without_secret_values(self) -> None:
        with patch.dict("os.environ", {"SENTRY_AUTH_TOKEN": "secret-token"}, clear=False):
            snapshot = vault_operator_snapshot()
        self.assertIn("consumers", snapshot)
        self.assertIn("known_keys", snapshot)
        self.assertEqual(list(ALLOWED_IMPORT_KEYS), snapshot["known_keys"])
        sentry = next(item for item in snapshot["consumers"] if item["id"] == "dashpro_sentry")
        self.assertEqual("ready", sentry["status"])
        self.assertIn("SENTRY_AUTH_TOKEN", sentry["satisfied_keys"])
        self.assertNotIn("secret-token", str(snapshot))

    def test_operator_snapshot_surfaces_runtime_consumers(self) -> None:
        with patch.dict("os.environ", {"CURSOR_API_KEY": "cursor-secret"}, clear=False):
            snapshot = vault_operator_snapshot()
        cursor = next(item for item in snapshot["consumers"] if item["id"] == "cursor_runtime")
        self.assertEqual("ready", cursor["status"])
        self.assertIn("CURSOR_API_KEY", cursor["satisfied_keys"])
        self.assertNotIn("cursor-secret", str(snapshot))

    @patch("app.vault.snapshot.probe_cursor_cli_subscription", return_value=_cursor_subscription_ready())
    def test_cursor_consumer_ready_via_cli_subscription_without_vault_key(
        self,
        _mock_probe: object,
    ) -> None:
        env = {key: "" for key in ("CURSOR_API_KEY", "CODEX_API_KEY", "OPENAI_API_KEY")}
        with patch.dict("os.environ", env, clear=False):
            snapshot = vault_operator_snapshot()
        cursor = next(item for item in snapshot["consumers"] if item["id"] == "cursor_runtime")
        self.assertEqual("ready", cursor["status"])
        self.assertIn("cli_subscription:operator@example.com", cursor["satisfied_keys"])
        self.assertNotIn("subscription_or_api_key", cursor["missing_keys"])
        self.assertIn("auth_note", cursor)
        self.assertTrue(cursor["subscription_auth"]["logged_in"])

    @patch("app.vault.snapshot.probe_cursor_cli_subscription", return_value=_cursor_subscription_missing())
    def test_cursor_consumer_partial_when_cli_installed_but_not_logged_in(
        self,
        _mock_probe: object,
    ) -> None:
        env = {key: "" for key in ("CURSOR_API_KEY", "CODEX_API_KEY", "OPENAI_API_KEY")}
        with patch.dict("os.environ", env, clear=False):
            snapshot = vault_operator_snapshot()
        cursor = next(item for item in snapshot["consumers"] if item["id"] == "cursor_runtime")
        self.assertEqual("partial", cursor["status"])
        self.assertIn("subscription_or_api_key", cursor["missing_keys"])

    def test_merge_vault_import_filters_unknown_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            with patch("app.vault.credential_resolver._state_dir", return_value=state_dir):
                result = merge_vault_import(
                    {
                        "SENTRY_AUTH_TOKEN": "abc123",
                        "NOT_ALLOWED": "ignored",
                    },
                    allowed_keys=ALLOWED_IMPORT_KEYS,
                )
                self.assertEqual(["SENTRY_AUTH_TOKEN"], result["imported_keys"])
                self.assertEqual(1, result["count"])


if __name__ == "__main__":
    unittest.main()
