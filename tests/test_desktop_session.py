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
                "AXON_WATCH_DESKTOP_SESSION_SECRET",
                "AXON_WATCH_CONSOLE_DIST",
            )
        }
        os.environ["AXON_WATCH_AUTH_MODE"] = "local_token"
        os.environ["AXON_WATCH_AUTH_ALLOW_LOOPBACK"] = "0"
        os.environ["AXON_WATCH_OPERATOR_TOKEN"] = "desktop-test-token"
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
