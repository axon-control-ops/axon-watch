from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
sys.path.insert(0, str(WATCH_ROOT))

from app.vault.backup import (  # noqa: E402
    BACKUP_FORMAT,
    build_backup_payload,
    decrypt_backup_file,
    encrypt_backup_payload,
)
from app.vault.crypto import decrypt, derive_key, encrypt, verify_totp  # noqa: E402
from app.vault.session import VaultSession  # noqa: E402


class VaultCryptoTests(unittest.TestCase):
    def test_encrypt_decrypt_round_trip(self) -> None:
        key = derive_key("test-password", b"s" * 32)
        encoded = encrypt("secret-value", key)
        self.assertEqual(decrypt(encoded, key), "secret-value")

    def test_totp_verify(self) -> None:
        import pyotp

        secret = pyotp.random_base32()
        code = pyotp.TOTP(secret).now()
        self.assertTrue(verify_totp(secret, code))


class VaultBackupTests(unittest.TestCase):
    def test_round_trip_encrypts_and_decrypts_secrets(self) -> None:
        payload = build_backup_payload(
            [
                {
                    "name": "Anthropic",
                    "category": "key",
                    "username": "",
                    "password": "sk-test",
                    "url": "https://api.anthropic.com",
                    "notes": "primary",
                }
            ],
            source_host="test-host",
        )
        encrypted = encrypt_backup_payload(payload, "backup-passphrase-123")
        restored = decrypt_backup_file(encrypted, "backup-passphrase-123")
        self.assertEqual(restored["format"], BACKUP_FORMAT)
        self.assertEqual(restored["secret_count"], 1)
        self.assertEqual(restored["secrets"][0]["name"], "Anthropic")
        self.assertEqual(restored["secrets"][0]["password"], "sk-test")

    def test_wrong_password_rejected(self) -> None:
        payload = build_backup_payload([{"name": "GH_TOKEN", "password": "abc"}])
        encrypted = encrypt_backup_payload(payload, "correct-password")
        with self.assertRaisesRegex(ValueError, "incorrect"):
            decrypt_backup_file(encrypted, "wrong-password")


class VaultOperationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._state = Path(self._tmpdir.name)
        os.environ["AXON_WATCH_STATE_DIR"] = str(self._state)
        VaultSession.lock()
        self.addCleanup(self._tmpdir.cleanup)
        self.addCleanup(VaultSession.lock)

    @patch("app.vault.operations.verify_totp", return_value=True)
    def test_setup_unlock_crud_provider_resolution(self, _mock_totp) -> None:
        from app.vault import operations

        setup = operations.setup_vault("master-password-123")
        self.assertIn("totp_secret", setup)
        ok, err = operations.unlock_vault("master-password-123", "123456")
        self.assertTrue(ok, err)
        secret_id = operations.vault_add_secret(
            VaultSession.get_key(),
            "Anthropic",
            "key",
            "",
            "sk-live-test",
            "https://api.anthropic.com",
            "",
        )
        self.assertGreater(secret_id, 0)
        listed = operations.vault_list_secrets()
        self.assertEqual(len(listed), 1)
        resolved = operations.vault_resolve_provider_key("anthropic")
        self.assertEqual(resolved, "sk-live-test")
        status = operations.vault_provider_key_status()
        self.assertTrue(status["unlocked"])
        self.assertTrue(status["resolved"].get("anthropic"))
        operations.lock_vault()
        self.assertFalse(VaultSession.is_unlocked())


class VaultRuntimeEnvTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        os.environ["AXON_WATCH_STATE_DIR"] = self._tmpdir.name
        VaultSession.lock()
        self.addCleanup(self._tmpdir.cleanup)
        self.addCleanup(VaultSession.lock)

    @patch("app.vault.operations.verify_totp", return_value=True)
    def test_vault_runtime_env_resolves_named_cursor_key(self, _mock_totp) -> None:
        from app.vault import operations

        operations.setup_vault("master-password-123")
        operations.unlock_vault("master-password-123", "123456")
        key = VaultSession.get_key()
        self.assertIsNotNone(key)
        operations.vault_add_secret(key, "CURSOR_API_KEY", "key", "", "sk-runtime-test", "", "")
        env = operations.vault_runtime_env()
        self.assertEqual("sk-runtime-test", env["CURSOR_API_KEY"])

    @patch("app.vault.operations.verify_totp", return_value=True)
    def test_vault_runtime_env_resolves_supabase_access_token(self, _mock_totp) -> None:
        from app.vault import operations

        operations.setup_vault("master-password-123")
        operations.unlock_vault("master-password-123", "123456")
        key = VaultSession.get_key()
        self.assertIsNotNone(key)
        operations.vault_add_secret(
            key,
            "SUPABASE_ACCESS_TOKEN",
            "key",
            "",
            "sbp_test_access_token",
            "https://supabase.com/dashboard/account/tokens",
            "",
        )
        env = operations.vault_runtime_env()
        self.assertEqual("sbp_test_access_token", env["SUPABASE_ACCESS_TOKEN"])

    @patch("app.vault.operations.verify_totp", return_value=True)
    def test_vault_runtime_env_resolves_azure_speech_credentials(self, _mock_totp) -> None:
        from app.vault import operations

        operations.setup_vault("master-password-123")
        operations.unlock_vault("master-password-123", "123456")
        key = VaultSession.get_key()
        self.assertIsNotNone(key)
        operations.vault_add_secret(
            key,
            "azure_speech_key",
            "key",
            "",
            "abc1234567890123456789012345678",
            "",
            "",
        )
        operations.vault_add_secret(
            key,
            "azure_speech_region",
            "key",
            "",
            "eastus",
            "",
            "",
        )

        env = operations.vault_runtime_env()
        self.assertEqual(env["AZURE_SPEECH_KEY"], "abc1234567890123456789012345678")
        self.assertEqual(env["AZURE_SPEECH_REGION"], "eastus")


if __name__ == "__main__":
    unittest.main()
