"""Gate 2 auth containment proofs: mutating API identity + worker Cursor policy."""

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

from app.auth.middleware import resolve_mutating_identity  # noqa: E402
from app.auth.settings import is_remotely_reachable  # noqa: E402
from tests.support.control_plane_app_loader import (  # noqa: E402
    load_control_plane_app,
    prepare_control_plane_imports,
)
from tests.support.watch_app_loader import load_watch_app, restore_app_modules  # noqa: E402
from tests.support.watch_db import isolate_watch_db  # noqa: E402


class _FakeRequest:
    def __init__(self, *, host: str | None, authorization: str = "", token_header: str = "") -> None:
        self.client = type("C", (), {"host": host})() if host is not None else None
        self.headers = {}
        self.cookies = {}
        if authorization:
            self.headers["authorization"] = authorization
        if token_header:
            self.headers["x-axon-operator-token"] = token_header


class Gate2OriginGuardTests(unittest.TestCase):
    def test_rejects_mismatched_origin_when_remotely_reachable(self) -> None:
        from app.auth.origin_guard import reject_cross_origin_mutation
        from starlette.requests import Request

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": "/api/runs",
            "raw_path": b"/api/runs",
            "query_string": b"",
            "headers": [(b"origin", b"https://evil.example")],
            "client": ("10.0.0.2", 443),
            "server": ("axon.example.com", 443),
        }
        request = Request(scope)
        with patch.dict(
            os.environ,
            {
                "AXON_WATCH_PUBLIC_BASE_URL": "https://axon.example.com",
                "AXON_WATCH_REMOTELY_REACHABLE": "1",
            },
            clear=False,
        ):
            detail = reject_cross_origin_mutation(request)
        self.assertIsNotNone(detail)
        self.assertIn("cross-origin", detail or "")

    def test_allows_matching_origin_and_missing_origin(self) -> None:
        from app.auth.origin_guard import reject_cross_origin_mutation
        from starlette.requests import Request

        def make(headers: list[tuple[bytes, bytes]]) -> Request:
            return Request(
                {
                    "type": "http",
                    "asgi": {"version": "3.0"},
                    "http_version": "1.1",
                    "method": "POST",
                    "scheme": "https",
                    "path": "/api/runs",
                    "raw_path": b"/api/runs",
                    "query_string": b"",
                    "headers": headers,
                    "client": ("10.0.0.2", 443),
                    "server": ("axon.example.com", 443),
                }
            )

        with patch.dict(
            os.environ,
            {
                "AXON_WATCH_PUBLIC_BASE_URL": "https://axon.example.com",
                "AXON_WATCH_REMOTELY_REACHABLE": "1",
            },
            clear=False,
        ):
            self.assertIsNone(
                reject_cross_origin_mutation(
                    make([(b"origin", b"https://axon.example.com")])
                )
            )
            self.assertIsNone(reject_cross_origin_mutation(make([])))


class Gate2AuthSettingsTests(unittest.TestCase):
    def test_remotely_reachable_from_public_base_url(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AXON_WATCH_PUBLIC_BASE_URL": "https://axon.example.com",
                "AXON_WATCH_REMOTELY_REACHABLE": "",
            },
            clear=False,
        ):
            self.assertTrue(is_remotely_reachable())
        with patch.dict(
            os.environ,
            {
                "AXON_WATCH_PUBLIC_BASE_URL": "http://127.0.0.1:4173",
                "AXON_WATCH_REMOTELY_REACHABLE": "",
            },
            clear=False,
        ):
            self.assertFalse(is_remotely_reachable())


class Gate2MutatingAuthMiddlewareTests(unittest.TestCase):
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

    def test_anonymous_mutation_denied_when_token_required(self) -> None:
        response = self.client.post(
            "/api/runs",
            json={"workspace_id": "workspace_axon_watch", "summary": "x", "mode": "agent"},
        )
        self.assertEqual(401, response.status_code)
        body = response.json()
        self.assertTrue(body.get("auth_required"))

    def test_bearer_token_allows_mutation(self) -> None:
        response = self.client.post(
            "/api/runs",
            json={"workspace_id": "workspace_axon_watch", "summary": "auth ok", "mode": "agent"},
            headers={"Authorization": "Bearer gate2-secret-token"},
        )
        self.assertEqual(200, response.status_code)
        self.assertIn("run_id", response.json())

    def test_cross_origin_mutation_forbidden_when_remote(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AXON_WATCH_PUBLIC_BASE_URL": "https://axon.example.com",
                "AXON_WATCH_REMOTELY_REACHABLE": "1",
            },
            clear=False,
        ):
            response = self.client.post(
                "/api/runs",
                json={
                    "workspace_id": "workspace_axon_watch",
                    "summary": "csrf",
                    "mode": "agent",
                },
                headers={
                    "Authorization": "Bearer gate2-secret-token",
                    "Origin": "https://evil.example",
                },
            )
        self.assertEqual(403, response.status_code)
        self.assertTrue(response.json().get("csrf_blocked"))

    def test_health_remains_public(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(200, response.status_code)

    def test_resolve_identity_loopback_bypass(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AXON_WATCH_AUTH_MODE": "local_token",
                "AXON_WATCH_OPERATOR_TOKEN": "gate2-secret-token",
                "AXON_WATCH_AUTH_ALLOW_LOOPBACK": "1",
            },
            clear=False,
        ):
            identity, err = resolve_mutating_identity(_FakeRequest(host="127.0.0.1"))
            self.assertEqual("loopback", identity)
            self.assertIsNone(err)


class Gate2WorkerTrustPolicyTests(unittest.TestCase):
    def test_worker_policy_omits_force_and_approve_mcps(self) -> None:
        from app.cli_runtime.cursor_agent import build_cursor_agent_command

        with patch("app.cli_runtime.cursor_agent.ensure_workspace_research_mcp"):
            command = build_cursor_agent_command(
                binary="cursor",
                prompt="hi",
                workspace_root=Path("."),
                composer_mode="agent",
                execution_tier="executing",
                trust_policy="worker",
                research_available=True,
            )
        self.assertIn("--trust", command)
        self.assertNotIn("--force", command)
        self.assertNotIn("--approve-mcps", command)

    def test_operator_policy_keeps_force_when_research_available(self) -> None:
        from app.cli_runtime.cursor_agent import build_cursor_agent_command

        with patch("app.cli_runtime.cursor_agent.ensure_workspace_research_mcp"):
            command = build_cursor_agent_command(
                binary="cursor",
                prompt="hi",
                workspace_root=Path("."),
                composer_mode="agent",
                execution_tier="executing",
                trust_policy="operator",
                research_available=True,
            )
        self.assertIn("--force", command)
        self.assertIn("--approve-mcps", command)


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
                "AXON_WATCH_AUTH_MODE": "off",
                "AXON_WATCH_PUBLIC_BASE_URL": "https://axon.example.com",
                "AXON_WATCH_REMOTELY_REACHABLE": "1",
                "AXON_WATCH_STATE_DIR": tmpdir.name,
                "AXON_WATCH_AUTH_AUDIT_LOG": str(Path(tmpdir.name) / "audit.ndjson"),
            },
            clear=False,
        ):
            app = load_control_plane_app()
            client = TestClient(app)
            response = client.post("/api/vault/auto-unlock/enable")
            self.assertEqual(403, response.status_code)
            audit = Path(tmpdir.name, "audit.ndjson").read_text(encoding="utf-8")
            self.assertIn("vault_auto_unlock_enable", audit)


class Gate2WatchInternalTokenTests(unittest.TestCase):
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

    def test_mutating_watch_route_denied_without_token(self) -> None:
        response = self.client.post(
            "/internal/watch/commands",
            json={
                "command_type": "reprobe_connector",
                "target_type": "connector",
                "target_id": "control_plane",
            },
        )
        self.assertEqual(401, response.status_code)
        self.assertTrue(response.json().get("auth_required"))

    def test_mutating_watch_route_allowed_with_token(self) -> None:
        response = self.client.post(
            "/internal/watch/commands",
            json={
                "command_type": "reprobe_connector",
                "target_type": "connector",
                "target_id": "control_plane",
            },
            headers={"X-Axon-Internal-Token": "watch-internal-secret"},
        )
        # Auth passed the gate; command may succeed or fail for other reasons.
        self.assertNotEqual(401, response.status_code)

    def test_health_remains_public(self) -> None:
        response = self.client.get("/internal/watch/health")
        self.assertEqual(200, response.status_code)


if __name__ == "__main__":
    unittest.main()
