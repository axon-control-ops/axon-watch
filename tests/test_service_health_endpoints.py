from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from tests.support.watch_app_loader import load_watch_app, restore_app_modules

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"


class ControlPlaneHealthEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        sys.path.insert(0, str(CONTROL_PLANE_ROOT))
        from app.main import app  # noqa: WPS433

        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_health_endpoint_reports_ok(self) -> None:
        response = self.client.get("/api/health")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("control-plane", payload["service"])
        self.assertEqual("ok", payload["status"])
        self.assertTrue(payload["boot_id"])

    def test_readiness_endpoint_reports_ready(self) -> None:
        response = self.client.get("/api/readiness")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("ready", payload["status"])
        self.assertIn("watch_base_url", payload)
        self.assertIn("state_dir", payload)
        self.assertIn("mode", payload)


class WatchHealthEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        watch_app, self._cached_modules = load_watch_app()
        self.client = TestClient(watch_app)

    def tearDown(self) -> None:
        self.client.close()
        restore_app_modules(self._cached_modules)

    def test_health_endpoint_reports_ok(self) -> None:
        response = self.client.get("/internal/watch/health")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("axon-watch", payload["service"])
        self.assertEqual("ok", payload["status"])

    def test_readiness_endpoint_reports_ready(self) -> None:
        response = self.client.get("/internal/watch/readiness")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("ready", payload["status"])
        self.assertIn("bootstrap_notes", payload)


if __name__ == "__main__":
    unittest.main()
