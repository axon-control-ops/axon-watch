from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db
from tests.support.ephemeral_uvicorn import EphemeralUvicorn
from tests.support.stable_connector_probe import (
    patch_stable_connector_probes,
    reset_watch_ephemeral_stores,
)
from tests.support.watch_app_loader import (
    load_control_plane_watch_pair,
    restore_app_modules,
)
from tests.support.watch_db import isolate_watch_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402
from app import runtime_summary_assembler  # noqa: E402


class ControlPlaneConnectorsTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_watch_db(self)
        self._connector_patch = patch_stable_connector_probes()

        def _prepare_watch() -> None:
            reset_watch_ephemeral_stores()
            self._connector_patch.start()

        watch_asgi, self._control_plane_modules = load_control_plane_watch_pair(
            on_watch_loaded=_prepare_watch,
        )
        self.addCleanup(self._connector_patch.stop)
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

        self._runtime_patch = patch.object(
            runtime_summary_assembler,
            "runtime_status_snapshot",
            return_value={
                "default_runtime": "cursor_local",
                "local": [
                    {
                        "id": "cursor_local",
                        "label": "Cursor CLI (local)",
                        "ready": True,
                        "available": True,
                        "auth": {"message": "Test runtime ready."},
                    }
                ],
            },
        )
        self._runtime_patch.start()
        self.addCleanup(self._runtime_patch.stop)

        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def tearDown(self) -> None:
        self._watch_server.stop()
        restore_app_modules(self._control_plane_modules)

    def test_connectors_endpoint_proxies_watch_connectors(self) -> None:
        response = self.client.get("/api/connectors")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertGreaterEqual(payload["count"], 2)
        self.assertTrue(payload["summary"]["configured"] >= 2)

    def test_runtime_summary_includes_connector_snapshot(self) -> None:
        response = self.client.get("/api/runtime/summary")
        self.assertEqual(200, response.status_code)
        connectors = response.json()["connectors"]
        self.assertGreaterEqual(connectors["configured"], 2)
        self.assertIn("last_updated_at", connectors)


if __name__ == "__main__":
    unittest.main()
