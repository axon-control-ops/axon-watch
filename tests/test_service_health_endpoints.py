from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.watch_app_loader import load_watch_app, restore_app_modules
from tests.support.control_plane_app_loader import load_control_plane_app

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"


class ControlPlaneHealthEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = patch.dict(os.environ, {}, clear=True)
        self._env.start()
        app = load_control_plane_app()
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.addCleanup(self._env.stop)

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

    def test_health_endpoint_allows_local_web_origin_via_cors(self) -> None:
        for origin in ("http://localhost:8081", "http://localhost:19006"):
            with self.subTest(origin=origin):
                response = self.client.get(
                    "/api/health",
                    headers={"Origin": origin},
                )

                self.assertEqual(200, response.status_code)
                self.assertEqual(
                    origin,
                    response.headers.get("access-control-allow-origin"),
                )

    def test_health_endpoint_allows_credentialed_local_web_origin_via_cors(self) -> None:
        for origin in ("http://127.0.0.1:8081", "http://127.0.0.1:19006"):
            with self.subTest(origin=origin):
                response = self.client.options(
                    "/api/health",
                    headers={
                        "Origin": origin,
                        "Access-Control-Request-Method": "GET",
                    },
                )

                self.assertEqual(200, response.status_code)
                self.assertEqual(
                    origin,
                    response.headers.get("access-control-allow-origin"),
                )
                self.assertEqual(
                    "true",
                    response.headers.get("access-control-allow-credentials"),
                )


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
