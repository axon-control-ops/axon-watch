"""Control-plane tunnel status proxy tests."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db
from tests.support.ephemeral_uvicorn import EphemeralUvicorn
from tests.support.watch_app_loader import load_control_plane_watch_pair, restore_app_modules

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402


class ControlPlaneTunnelTests(unittest.TestCase):
    def setUp(self) -> None:
        watch_asgi, self._control_plane_modules = load_control_plane_watch_pair()
        self._watch_server = EphemeralUvicorn(watch_asgi)
        self._watch_server.start("/internal/watch/health")

        isolate_control_plane_db(self, run_store)
        self._env_patch = patch.dict(
            os.environ,
            {"AXON_WATCH_WATCH_SERVICE_BASE_URL": self._watch_server.base_url},
            clear=False,
        )
        self._env_patch.start()
        self.addCleanup(self._env_patch.stop)

        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def tearDown(self) -> None:
        self._watch_server.stop()
        restore_app_modules(self._control_plane_modules)

    def test_tunnel_status_endpoint_proxies_watch(self) -> None:
        response = self.client.get("/api/tunnel/status")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertIn("mode", payload)
        self.assertIn("detail", payload)
        self.assertIn("auth_source", payload)

    def test_connectors_include_cloudflare_tunnel_record(self) -> None:
        response = self.client.get("/api/connectors")
        self.assertEqual(200, response.status_code)
        items = response.json()["items"]
        tunnel_items = [item for item in items if item.get("connector_id") == "cloudflare_tunnel"]
        self.assertEqual(1, len(tunnel_items))
        self.assertIn("tunnel", tunnel_items[0])


if __name__ == "__main__":
    unittest.main()
