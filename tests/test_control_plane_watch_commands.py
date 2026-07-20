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


class ControlPlaneWatchCommandsTests(unittest.TestCase):
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

    def test_watch_command_proxy_reprobe_connector(self) -> None:
        response = self.client.post(
            "/api/watch/commands",
            json={
                "command_type": "reprobe_connector",
                "target_type": "connector",
                "target_id": "control_plane",
            },
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("completed", payload["status"])
        command_id = payload["command_id"]

        show_response = self.client.get(f"/api/watch/commands/{command_id}")
        self.assertEqual(200, show_response.status_code)
        self.assertEqual("reprobe_connector", show_response.json()["command_type"])

    def test_watch_events_proxy_returns_items(self) -> None:
        self.client.post(
            "/api/watch/commands",
            json={"command_type": "refresh_summary"},
        )
        response = self.client.get("/api/watch/events?limit=5")
        self.assertEqual(200, response.status_code)
        self.assertGreaterEqual(response.json()["count"], 1)


if __name__ == "__main__":
    unittest.main()
