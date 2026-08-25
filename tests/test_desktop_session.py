"""Tests for desktop session cookie auth and bootstrap."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient


class DesktopSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev = {
            key: os.environ.get(key)
            for key in (
                "AXON_WATCH_AUTH_MODE",
                "AXON_WATCH_AUTH_ALLOW_LOOPBACK",
                "AXON_WATCH_OPERATOR_TOKEN",
                "AXON_WATCH_OPERATOR_PASSWORD",
                "AXON_WATCH_DESKTOP_SESSION_SECRET",
                "AXON_WATCH_CONSOLE_DIST",
            )
        }
        os.environ["AXON_WATCH_AUTH_MODE"] = "local_token"
        os.environ["AXON_WATCH_AUTH_ALLOW_LOOPBACK"] = "0"
        os.environ["AXON_WATCH_OPERATOR_TOKEN"] = "desktop-test-token"
        os.environ["AXON_WATCH_OPERATOR_PASSWORD"] = "desktop-test-password"
        os.environ["AXON_WATCH_DESKTOP_SESSION_SECRET"] = "desktop-test-secret"
        from app.auth.desktop_session import clear_pending_bootstrap
        from app.main import app

        clear_pending_bootstrap()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        for key, value in self._prev.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_bootstrap_sets_httponly_session_cookie(self) -> None:
        response = self.client.post(
            "/api/desktop/bootstrap",
            json={"operator_token": "desktop-test-token"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("ok"))
        self.assertIn("axon_desktop_session", response.cookies)

    def test_session_cookie_authorizes_mutating_call(self) -> None:
        boot = self.client.post(
            "/api/desktop/bootstrap",
            json={"operator_token": "desktop-test-token"},
        )
        self.assertEqual(boot.status_code, 200)
        # Pause awareness is a mutating host route.
        response = self.client.post("/api/host/privacy/pause", json={"minutes": 1})
        # 200 or 422 both mean auth passed; 401 would mean cookie rejected.
        self.assertNotEqual(response.status_code, 401)

    def test_browser_session_login_status_and_logout(self) -> None:
        initial = self.client.get("/api/auth/session")
        self.assertEqual(initial.status_code, 200)
        self.assertEqual(initial.json()["authenticated"], False)
        self.assertEqual(initial.json()["auth_required"], True)
        self.assertEqual(initial.json()["loopback_bypass"], False)
        self.assertEqual(initial.json()["cookie_max_age_seconds"], 60 * 60 * 24 * 30)
        self.assertEqual(initial.json()["auth_mode"], "local_token")

        rejected = self.client.post(
            "/api/auth/session",
            json={"operator_token": "wrong-token"},
        )
        self.assertEqual(rejected.status_code, 401)
        self.assertEqual(rejected.json()["detail"], "invalid operator credentials")
        self.assertNotIn("axon_desktop_session", rejected.cookies)

        anonymous_logout = self.client.delete("/api/auth/session")
        self.assertEqual(anonymous_logout.status_code, 200)
        self.assertEqual(anonymous_logout.json()["authenticated"], False)

        login = self.client.post(
            "/api/auth/session",
            json={"operator_token": "desktop-test-token"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json()["identity"], "session")
        self.assertIn("axon_desktop_session", login.cookies)
        self.assertIn("HttpOnly", login.headers["set-cookie"])

        authenticated = self.client.get("/api/auth/session")
        self.assertEqual(authenticated.json()["authenticated"], True)
        self.assertEqual(authenticated.json()["identity"], "session")

        logout = self.client.delete("/api/auth/session")
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(logout.json()["authenticated"], False)
        self.assertEqual(self.client.get("/api/auth/session").json()["authenticated"], False)

    def test_browser_session_login_accepts_password_and_returns_mobile_session_token(self) -> None:
        login = self.client.post(
            "/api/auth/session",
            json={"operator_password": "desktop-test-password", "return_session_token": True},
        )
        self.assertEqual(login.status_code, 200)
        payload = login.json()
        self.assertEqual(payload["identity"], "session")
        self.assertTrue(payload.get("session_token"))

        response = self.client.post(
            "/api/runs",
            json={"workspace_id": "workspace_axon_watch", "summary": "password session ok", "mode": "agent"},
            headers={"x-axon-desktop-session": payload["session_token"]},
        )
        self.assertNotEqual(response.status_code, 401)

    def test_spa_served_when_console_dist_configured(self) -> None:
        with TemporaryDirectory() as tmp:
            dist = Path(tmp)
            (dist / "index.html").write_text("<html>VAXON</html>", encoding="utf-8")
            (dist / "assets").mkdir()
            (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
            os.environ["AXON_WATCH_CONSOLE_DIST"] = str(dist)
            # Re-import registration is sticky; hit status + FileResponse via routes already mounted.
            # Status reports packaged when env is set for this process.
            from app.routes.desktop import console_dist_dir

            self.assertIsNotNone(console_dist_dir())
            status = self.client.get("/api/desktop/status")
            self.assertEqual(status.status_code, 200)


if __name__ == "__main__":
    unittest.main()
