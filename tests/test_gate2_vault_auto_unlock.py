"""Gate 2 vault auto-unlock: remote refuse vs trusted-host override."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from tests.support.control_plane_app_loader import (  # noqa: E402
    load_control_plane_app,
    prepare_control_plane_imports,
)


class Gate2VaultAutoUnlockRemoteTests(unittest.TestCase):
    def test_control_plane_refuses_enable_when_remote(self) -> None:
        prepare_control_plane_imports()
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        with patch.dict(
            os.environ,
            {
                "AXON_WATCH_CONTROL_PLANE_DB": str(Path(tmpdir.name) / "cp.sqlite3"),
                "AXON_WATCH_WORKER_SCHEDULER": "0",
                "AXON_WATCH_AUTH_MODE": "local_token",
                "AXON_WATCH_OPERATOR_TOKEN": "gate2-vault-token",
                "AXON_WATCH_AUTH_ALLOW_LOOPBACK": "0",
                "AXON_WATCH_PUBLIC_BASE_URL": "https://axon.example.com",
                "AXON_WATCH_REMOTELY_REACHABLE": "1",
                "AXON_WATCH_STATE_DIR": tmpdir.name,
                "AXON_WATCH_AUTH_AUDIT_LOG": str(Path(tmpdir.name) / "audit.ndjson"),
            },
            clear=False,
        ):
            app = load_control_plane_app()
            client = TestClient(app)
            response = client.post(
                "/api/vault/auto-unlock/enable",
                headers={"Authorization": "Bearer gate2-vault-token"},
            )
            self.assertEqual(403, response.status_code)
            audit = Path(tmpdir.name, "audit.ndjson").read_text(encoding="utf-8")
            self.assertIn("vault_auto_unlock_enable", audit)

    def test_control_plane_allows_enable_when_remote_override(self) -> None:
        prepare_control_plane_imports()
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        with patch.dict(
            os.environ,
            {
                "AXON_WATCH_CONTROL_PLANE_DB": str(Path(tmpdir.name) / "cp.sqlite3"),
                "AXON_WATCH_WORKER_SCHEDULER": "0",
                "AXON_WATCH_AUTH_MODE": "local_token",
                "AXON_WATCH_OPERATOR_TOKEN": "gate2-vault-token",
                "AXON_WATCH_AUTH_ALLOW_LOOPBACK": "0",
                "AXON_WATCH_PUBLIC_BASE_URL": "https://axon.example.com",
                "AXON_WATCH_REMOTELY_REACHABLE": "1",
                "AXON_WATCH_ALLOW_VAULT_AUTO_UNLOCK": "1",
                "AXON_WATCH_STATE_DIR": tmpdir.name,
                "AXON_WATCH_AUTH_AUDIT_LOG": str(Path(tmpdir.name) / "audit.ndjson"),
                "AXON_WATCH_WATCH_SERVICE_BASE_URL": "http://127.0.0.1:9",
            },
            clear=False,
        ):
            from app.auth.settings import vault_auto_unlock_allowed

            self.assertTrue(vault_auto_unlock_allowed())
            app = load_control_plane_app()
            client = TestClient(app)
            # Watch is unreachable in this unit test — expect proxy failure, not 403 refuse.
            response = client.post(
                "/api/vault/auto-unlock/enable",
                headers={"Authorization": "Bearer gate2-vault-token"},
            )
            self.assertNotEqual(403, response.status_code)


if __name__ == "__main__":
    unittest.main()
