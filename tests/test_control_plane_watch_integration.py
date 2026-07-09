"""Phase 5 E2E: control-plane calls the watch service through the documented contract."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.bootstrap_signal_fixture import BOOTSTRAP_SIGNAL_ID, consistency_tuple
from tests.support.control_plane_db import isolate_control_plane_db
from tests.support.ephemeral_uvicorn import EphemeralUvicorn
from tests.support.summary_degraded_signal_fixture import SUMMARY_DEGRADED_SIGNAL_ID
from tests.support.stable_connector_probe import (
    patch_stable_connector_probes,
    reset_watch_ephemeral_stores,
)
from tests.support.watch_app_loader import load_watch_app, restore_app_modules
from tests.support.watch_db import isolate_watch_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402


class ControlPlaneWatchIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_watch_db(self)
        watch_app, self._watch_modules = load_watch_app()
        reset_watch_ephemeral_stores()
        self._connector_patch = patch_stable_connector_probes()
        self._connector_patch.start()
        self.addCleanup(self._connector_patch.stop)
        self._watch_server = EphemeralUvicorn(watch_app)
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
        restore_app_modules(self._watch_modules)

    def test_inbox_endpoint_fetches_live_watch_inbox(self) -> None:
        response = self.client.get("/api/inbox")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(1, payload["count"])
        signal_ids = {item["signal_id"] for item in payload["items"]}
        self.assertIn(BOOTSTRAP_SIGNAL_ID, signal_ids)
        self.assertNotIn(SUMMARY_DEGRADED_SIGNAL_ID, signal_ids)

    def test_runtime_summary_marks_watch_connected_from_live_probe(self) -> None:
        response = self.client.get("/api/runtime/summary")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload["watch"]["connected"])
        self.assertFalse(payload["degraded"]["active"])
        # Bootstrap inbox noise is filtered from runtime summary signal counts.
        self.assertEqual(0, payload["signals"]["open_count"])
        self.assertEqual([], payload["signals"]["top_items"])
        self.assertGreaterEqual(payload["connectors"]["configured"], 2)

    def test_inbox_and_runtime_summary_agree_on_ranked_top_signal(self) -> None:
        inbox = self.client.get("/api/inbox").json()
        summary = self.client.get("/api/runtime/summary").json()
        inbox_item = inbox["items"][0]

        self.assertEqual(BOOTSTRAP_SIGNAL_ID, inbox_item["signal_id"])
        self.assertEqual(consistency_tuple(inbox_item), consistency_tuple(inbox["items"][0]))
        # Runtime summary intentionally omits bootstrap-only signals from top_items.
        self.assertEqual([], summary["signals"]["top_items"])
        self.assertEqual(0, summary["signals"]["open_count"])

    def test_inbox_signals_acknowledge_clears_active_signals(self) -> None:
        before = self.client.get("/api/inbox").json()
        signal_ids = [item["signal_id"] for item in before["items"]]
        self.assertGreater(len(signal_ids), 0)

        response = self.client.post(
            "/api/inbox/signals/acknowledge",
            json={"signal_ids": signal_ids},
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload["accepted"])
        self.assertEqual(len(signal_ids), payload["count"])

        after = self.client.get("/api/inbox").json()
        self.assertEqual(0, after["count"])

        summary = self.client.get("/api/runtime/summary").json()
        self.assertEqual(0, summary["signals"]["open_count"])


if __name__ == "__main__":
    unittest.main()
