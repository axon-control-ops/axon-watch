from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime import catalog, vault_keys  # noqa: E402
from app.cli_runtime.auth_probes import codex_auth_status  # noqa: E402


class RuntimeVaultIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        catalog._SNAPSHOT_CACHE["fetched_at"] = 0.0
        catalog._SNAPSHOT_CACHE["payload"] = None
        vault_keys.invalidate_runtime_vault_cache()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.environ["AXON_WATCH_STATE_DIR"] = self._tmpdir.name
        self.addCleanup(self._tmpdir.cleanup)
        self.addCleanup(vault_keys.invalidate_runtime_vault_cache)

    @patch("app.cli_runtime.catalog_snapshot.fetch_runtime_context")
    @patch("app.cli_runtime.catalog.find_cursor_cli", return_value="/usr/bin/cursor")
    @patch("app.cli_runtime.catalog.find_claude_cli", return_value="")
    @patch("app.cli_runtime.catalog.find_codex_cli", return_value="")
    @patch("app.cli_runtime.auth_probes._run_command")
    def test_runtime_status_marks_vault_locked_without_cli_login(
        self,
        mock_run,
        _find_codex,
        _find_claude,
        _find_cursor,
        mock_fetch_context,
    ) -> None:
        mock_fetch_context.return_value = {
            "vault_runtime": {
                "unlocked": False,
                "posture": "vault_locked",
                "hint": "Unlock /vault to inject provider keys into CLI runtimes.",
                "runtime_keys": {"cursor_local": False},
                "provider_keys": {"cursor_cli": False},
            },
            "env": {},
        }
        snapshot = catalog.runtime_status_snapshot(force_refresh=True)
        self.assertEqual("vault_locked", snapshot["vault_runtime"]["posture"])
        cursor = snapshot["local"][0]
        self.assertFalse(cursor["ready"])
        self.assertEqual("vault_locked", cursor["auth"]["vault_posture"])

    @patch("app.cli_runtime.catalog_snapshot.fetch_runtime_context")
    @patch("app.cli_runtime.catalog.find_cursor_cli", return_value="/usr/bin/cursor")
    @patch("app.cli_runtime.catalog.find_claude_cli", return_value="")
    @patch("app.cli_runtime.catalog.find_codex_cli", return_value="")
    @patch("app.cli_runtime.auth_probes._run_command")
    def test_runtime_status_ready_when_vault_feeds_cursor_key(
        self,
        mock_run,
        _find_codex,
        _find_claude,
        _find_cursor,
        mock_fetch_context,
    ) -> None:
        def _auth_probe(parts: list[str], *, timeout: int = 8, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
            if env and str(env.get("CURSOR_API_KEY", "")).strip():
                return subprocess.CompletedProcess(
                    args=parts,
                    returncode=0,
                    stdout="cursor account ready",
                    stderr="",
                )
            return subprocess.CompletedProcess(
                args=parts,
                returncode=1,
                stdout="not logged in",
                stderr="",
            )

        mock_run.side_effect = _auth_probe
        mock_fetch_context.return_value = {
            "vault_runtime": {
                "unlocked": True,
                "posture": "ready",
                "hint": "Vault provider keys are available for CLI runtimes.",
                "runtime_keys": {"cursor_local": True, "cursor_cloud": True},
                "provider_keys": {"cursor_cli": True},
            },
            "env": {"CURSOR_API_KEY": "sk-from-vault"},
        }
        snapshot = catalog.runtime_status_snapshot(force_refresh=True)
        cursor = snapshot["local"][0]
        self.assertTrue(cursor["ready"])
        self.assertEqual("vault_api_key", cursor["auth"]["auth_method"])

    def test_runtime_subprocess_env_prefers_existing_process_env(self) -> None:
        with patch.dict(os.environ, {"CURSOR_API_KEY": "from-process"}, clear=False):
            with patch(
                "app.cli_runtime.vault_keys.runtime_vault_env",
                return_value={"CURSOR_API_KEY": "from-vault"},
            ):
                merged = vault_keys.runtime_subprocess_env(force_refresh=True)
        self.assertEqual("from-process", merged["CURSOR_API_KEY"])

    def test_runtime_subprocess_env_includes_supabase_access_token_from_vault(self) -> None:
        with patch(
            "app.cli_runtime.vault_keys.runtime_vault_env",
            return_value={"SUPABASE_ACCESS_TOKEN": "sbp_from_vault"},
        ):
            merged = vault_keys.runtime_subprocess_env(force_refresh=True)
        self.assertEqual("sbp_from_vault", merged["SUPABASE_ACCESS_TOKEN"])

    def test_watch_runtime_env_exports_workspace_service_keys(self) -> None:
        import importlib.util

        path = WATCH_ROOT / "app" / "vault" / "runtime_env.py"
        spec = importlib.util.spec_from_file_location("watch_runtime_env_test", path)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)

        class FakeVaultSession:
            @staticmethod
            def is_unlocked() -> bool:
                return True

        secrets = {
            "GH_TOKEN": "ghp_from_vault",
            "SENTRY_AUTH_TOKEN": "sentry_from_vault",
            "SUPABASE_ACCESS_TOKEN": "sbp_from_vault",
        }

        module.VaultSession = FakeVaultSession
        module.vault_resolve_named_secret = lambda name: secrets.get(name, "")
        module.vault_resolve_provider_key = lambda _provider_id: ""
        module.vault_resolve_all_provider_keys = lambda: {}
        spec.loader.exec_module(module)

        env = module.vault_runtime_env()
        self.assertEqual("ghp_from_vault", env["GH_TOKEN"])
        self.assertEqual("sentry_from_vault", env["SENTRY_AUTH_TOKEN"])
        self.assertEqual("sbp_from_vault", env["SUPABASE_ACCESS_TOKEN"])

    @patch("app.cli_runtime.auth_probes._run_command")
    def test_codex_prefers_chatgpt_session_over_vault_key(self, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["codex", "login", "status"],
            returncode=0,
            stdout="Logged in using ChatGPT",
            stderr="",
        )
        status = codex_auth_status(
            "/usr/bin/codex",
            vault_posture={"unlocked": True, "posture": "ready", "runtime_keys": {"codex_local": True}},
            env_keys={"CODEX_API_KEY": "stale-vault-key"},
            probe_env={"CODEX_API_KEY": "stale-vault-key"},
        )
        self.assertTrue(status["logged_in"])
        self.assertEqual("chatgpt", status["auth_method"])
        self.assertIn("ignored", status["message"])

    @patch("app.cli_runtime.vault_keys.watch_adapter.request_json", side_effect=RuntimeError("HTTP 404"))
    def test_runtime_context_falls_back_when_watch_runtime_posture_is_missing(self, _mock_request) -> None:
        payload = vault_keys.fetch_runtime_context(force_refresh=True)
        posture = payload["vault_runtime"]
        self.assertEqual("vault_locked", posture["posture"])
        self.assertFalse(posture["unlocked"])
        self.assertEqual({}, payload["env"])


if __name__ == "__main__":
    unittest.main()
