from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime import catalog  # noqa: E402


class CliRuntimeCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        catalog._SNAPSHOT_CACHE["fetched_at"] = 0.0
        catalog._SNAPSHOT_CACHE["payload"] = None
        catalog._SNAPSHOT_REFRESH_THREAD = None

    @patch("app.cli_runtime.catalog_snapshot.schedule_runtime_status_refresh")
    def test_allow_stale_returns_cache_without_blocking_probe(self, mock_schedule) -> None:
        catalog._SNAPSHOT_CACHE["payload"] = {
            "updated_at": "2026-07-18T00:00:00Z",
            "default_runtime": "cursor_local",
            "vault_runtime": {},
            "local": [{"id": "cursor_local", "ready": True}],
            "cloud": [],
        }
        catalog._SNAPSHOT_CACHE["fetched_at"] = 0.0  # expired TTL
        snapshot = catalog.runtime_status_snapshot(allow_stale=True)
        self.assertEqual("cursor_local", snapshot["default_runtime"])
        mock_schedule.assert_called()

    @patch("app.cli_runtime.catalog_snapshot.fetch_runtime_context")
    @patch("app.cli_runtime.catalog.find_cursor_cli", return_value="/usr/bin/cursor")
    @patch("app.cli_runtime.catalog.find_codex_cli", return_value="/usr/bin/codex")
    @patch("app.cli_runtime.auth_probes._run_command")
    def test_runtime_status_prefers_ready_cursor_local(
        self,
        mock_run,
        _find_codex,
        _find_cursor,
        mock_fetch_context,
    ) -> None:
        mock_fetch_context.return_value = {
            "vault_runtime": {
                "unlocked": False,
                "posture": "vault_locked",
                "hint": "Unlock /vault",
                "runtime_keys": {},
                "provider_keys": {},
            },
            "env": {},
        }
        mock_run.return_value = type(
            "Proc",
            (),
            {"returncode": 0, "stdout": "Logged in as operator", "stderr": ""},
        )()
        snapshot = catalog.runtime_status_snapshot(force_refresh=True)
        self.assertEqual("cursor_local", snapshot["default_runtime"])
        self.assertEqual(2, len(snapshot["local"]))
        self.assertEqual("cursor_local", snapshot["local"][0]["id"])
        self.assertTrue(snapshot["local"][0]["ready"])

    @patch("app.cli_runtime.catalog.runtime_status_snapshot")
    def test_runtime_identity_reflects_selected_runtime(self, mock_snapshot) -> None:
        mock_snapshot.return_value = {
            "default_runtime": "codex_local",
            "local": [
                {
                    "id": "cursor_local",
                    "family": "cursor",
                    "target_type": "local",
                    "available": True,
                    "ready": False,
                },
                {
                    "id": "codex_local",
                    "family": "codex",
                    "target_type": "local",
                    "available": True,
                    "ready": True,
                },
            ],
            "cloud": [],
        }
        identity = catalog.runtime_identity_snapshot()
        self.assertEqual("codex_local", identity["provider_family"])
        self.assertEqual("Codex CLI", identity["provider_name"])
        self.assertTrue(identity["tool_calling_supported"])


if __name__ == "__main__":
    unittest.main()
