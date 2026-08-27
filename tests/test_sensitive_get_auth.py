"""Sensitive GET routes require identity when token mode is on."""

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
from tests.support.watch_app_loader import load_watch_app, restore_app_modules  # noqa: E402
from tests.support.watch_db import isolate_watch_db  # noqa: E402


class VaultSensitiveGetTests(unittest.TestCase):
    def setUp(self) -> None:
        prepare_control_plane_imports()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self._env = patch.dict(
            os.environ,
            {
                "AXON_WATCH_CONTROL_PLANE_DB": str(Path(self._tmpdir.name) / "cp.sqlite3"),
                "AXON_WATCH_WORKER_SCHEDULER": "0",
                "AXON_WATCH_AUTH_MODE": "local_token",
                "AXON_WATCH_OPERATOR_TOKEN": "gate2-secret-token",
                "AXON_WATCH_AUTH_ALLOW_LOOPBACK": "0",
                "AXON_WATCH_STATE_DIR": self._tmpdir.name,
            },
            clear=False,
        )
        self._env.start()
        self.addCleanup(self._env.stop)
        self.app = load_control_plane_app()
        self.client = TestClient(self.app)

    def test_anonymous_vault_secrets_denied(self) -> None:
        response = self.client.get("/api/vault/secrets")
        self.assertEqual(401, response.status_code)
        self.assertTrue(response.json().get("auth_required"))

    def test_anonymous_vault_export_csv_denied(self) -> None:
        response = self.client.get("/api/vault/export/csv")
        self.assertEqual(401, response.status_code)

    def test_bearer_token_passes_operator_identity_gate(self) -> None:
        # Keep this test at the control-plane boundary. Calling the live Watch
        # service would conflate its internal-service token with the operator
        # bearer token this test is meant to verify.
        with patch("app.routes.vault_http.list_vault_secrets", return_value=[]):
            response = self.client.get(
                "/api/vault/secrets",
                headers={"Authorization": "Bearer gate2-secret-token"},
            )
        self.assertEqual(200, response.status_code)
        self.assertEqual([], response.json())


class OperatorSensitiveGetTests(unittest.TestCase):
    def setUp(self) -> None:
        prepare_control_plane_imports()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self._env = patch.dict(
            os.environ,
            {
                "AXON_WATCH_CONTROL_PLANE_DB": str(Path(self._tmpdir.name) / "cp.sqlite3"),
                "AXON_WATCH_WORKER_SCHEDULER": "0",
                "AXON_WATCH_AUTH_MODE": "local_token",
                "AXON_WATCH_OPERATOR_TOKEN": "gate2-secret-token",
                "AXON_WATCH_AUTH_ALLOW_LOOPBACK": "0",
                "AXON_WATCH_STATE_DIR": self._tmpdir.name,
            },
            clear=False,
        )
        self._env.start()
        self.addCleanup(self._env.stop)
        self.app = load_control_plane_app()
        self.client = TestClient(self.app)

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer gate2-secret-token"}

    def test_operator_run_recovery_and_evidence_reads_deny_anonymous(self) -> None:
        for path in (
            "/api/runs",
            "/api/recovery/center",
            "/api/recovery/circuits",
            "/api/platform/doctor",
            "/api/operator/evidence?node_id=core_kairo",
            "/api/data/snapshot",
            "/api/workspaces",
            "/api/inbox",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(401, response.status_code)
                self.assertTrue(response.json().get("auth_required"))

    def test_bearer_token_allows_operator_run_and_recovery_reads(self) -> None:
        for path in (
            "/api/runs",
            "/api/recovery/center",
            "/api/operator/evidence?node_id=core_kairo",
            "/api/workspaces",
        ):
            with self.subTest(path=path):
                response = self.client.get(path, headers=self._auth_headers())
                self.assertNotEqual(401, response.status_code)
                self.assertNotEqual(403, response.status_code)

    def test_run_history_and_task_reads_require_operator_identity(self) -> None:
        created = self.client.post(
            "/api/workspaces/workspace_axon_watch/tasks",
            json={
                "goal": "Repair sensitive GET auth.",
                "acceptance_criteria": "Authorization regression tests pass.",
                "owner_role": "backend",
            },
            headers=self._auth_headers(),
        ).json()
        run = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_axon_watch",
                "summary": "auth-sensitive run",
                "mode": "agent",
            },
            headers=self._auth_headers(),
        ).json()

        for path in (
            f"/api/runs/{run['run_id']}",
            f"/api/runs/{run['run_id']}/history",
            f"/api/tasks/{created['task_id']}",
            "/api/workspaces/workspace_axon_watch/tasks",
        ):
            with self.subTest(path=path):
                denied = self.client.get(path)
                self.assertEqual(401, denied.status_code)
                allowed = self.client.get(path, headers=self._auth_headers())
                self.assertNotEqual(401, allowed.status_code)

    def test_health_remains_public_but_readiness_redacts_without_identity(self) -> None:
        health = self.client.get("/api/health")
        self.assertEqual(200, health.status_code)

        anonymous = self.client.get("/api/readiness")
        self.assertEqual(200, anonymous.status_code)
        self.assertEqual("redacted", anonymous.json().get("detail"))
        self.assertNotIn("state_dir", anonymous.json())
        self.assertNotIn("control_plane_db", anonymous.json())

        authenticated = self.client.get("/api/readiness", headers=self._auth_headers())
        self.assertEqual(200, authenticated.status_code)
        self.assertEqual("full", authenticated.json().get("detail"))
        self.assertIn("state_dir", authenticated.json())
        self.assertIn("control_plane_db", authenticated.json())

    def test_local_loopback_bypass_remains_deliberate_when_enabled(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AXON_WATCH_AUTH_ALLOW_LOOPBACK": "1",
                "AXON_WATCH_REMOTELY_REACHABLE": "0",
                "AXON_WATCH_PUBLIC_BASE_URL": "http://127.0.0.1:4173",
            },
            clear=False,
        ):
            loopback_client = TestClient(self.app, client=("127.0.0.1", 50000))
            self.addCleanup(loopback_client.close)
            response = loopback_client.get("/api/runs")
        self.assertEqual(200, response.status_code)


class WatchConfidentialGetTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_watch_db(self)
        self._env = patch.dict(
            os.environ,
            {"AXON_WATCH_INTERNAL_SERVICE_TOKEN": "watch-internal-secret"},
            clear=False,
        )
        self._env.start()
        self.addCleanup(self._env.stop)
        watch_app, self._watch_modules = load_watch_app()
        self.client = TestClient(watch_app)
        self.addCleanup(self.client.close)

    def tearDown(self) -> None:
        restore_app_modules(self._watch_modules)

    def test_anonymous_vault_secrets_denied(self) -> None:
        response = self.client.get("/internal/watch/vault/secrets")
        self.assertEqual(401, response.status_code)
        self.assertTrue(response.json().get("auth_required"))

    def test_token_allows_confidential_get_past_identity_gate(self) -> None:
        response = self.client.get(
            "/internal/watch/vault/secrets",
            headers={"X-Axon-Internal-Token": "watch-internal-secret"},
        )
        self.assertNotEqual(401, response.status_code)

    def test_health_remains_public(self) -> None:
        response = self.client.get("/internal/watch/health")
        self.assertEqual(200, response.status_code)


if __name__ == "__main__":
    unittest.main()
