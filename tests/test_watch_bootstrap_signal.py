from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from tests.support.bootstrap_signal_fixture import (
    BOOTSTRAP_SIGNAL_ID,
    BOOTSTRAP_INBOX_ITEM,
    CONSISTENCY_FIELDS,
    consistency_tuple,
)

from tests.support.stable_connector_probe import (
    patch_stable_connector_probes,
    reset_watch_ephemeral_stores,
)

WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"


def _load_watch_app():
    cached = {
        name: module
        for name, module in sys.modules.items()
        if name == "app" or name.startswith("app.")
    }
    for name in cached:
        del sys.modules[name]

    sys.path.insert(0, str(WATCH_ROOT))
    from app.main import app as watch_app  # noqa: WPS433

    return watch_app, cached


def _restore_modules(cached: dict[str, object]) -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    sys.modules.update(cached)


class WatchBootstrapSignalTests(unittest.TestCase):
    def setUp(self) -> None:
        self._cached_modules: dict[str, object] = {}
        watch_app, self._cached_modules = _load_watch_app()
        reset_watch_ephemeral_stores()
        self._connector_patch = patch_stable_connector_probes()
        self._connector_patch.start()
        self.addCleanup(self._connector_patch.stop)
        self.client = TestClient(watch_app)

    def tearDown(self) -> None:
        _restore_modules(self._cached_modules)

    def test_watch_inbox_returns_canonical_snapshot_shape(self) -> None:
        response = self.client.get("/internal/watch/inbox")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual({"items", "count", "updated_at"}, set(payload))
        self.assertEqual(2, payload["count"])
        self.assertEqual(2, len(payload["items"]))

    def test_watch_inbox_item_matches_bootstrap_signal_identity(self) -> None:
        response = self.client.get("/internal/watch/inbox")
        item = next(
            row for row in response.json()["items"] if row["signal_id"] == BOOTSTRAP_SIGNAL_ID
        )

        self.assertEqual(BOOTSTRAP_SIGNAL_ID, item["signal_id"])
        self.assertEqual(consistency_tuple(BOOTSTRAP_INBOX_ITEM), consistency_tuple(item))
        for field in CONSISTENCY_FIELDS:
            self.assertEqual(BOOTSTRAP_INBOX_ITEM[field], item[field])

    def test_watch_readiness_documents_expected_bootstrap_degraded_signal(self) -> None:
        response = self.client.get("/internal/watch/readiness")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        notes = payload["bootstrap_notes"]
        self.assertTrue(notes["summary_degraded_signal_expected"])
        self.assertIn("bootstrap", notes["detail"].lower())


if __name__ == "__main__":
    unittest.main()
