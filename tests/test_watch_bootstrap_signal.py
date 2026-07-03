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
        self.client = TestClient(watch_app)

    def tearDown(self) -> None:
        _restore_modules(self._cached_modules)

    def test_watch_inbox_returns_canonical_snapshot_shape(self) -> None:
        response = self.client.get("/internal/watch/inbox")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual({"items", "count", "updated_at"}, set(payload))
        self.assertEqual(1, payload["count"])
        self.assertEqual(1, len(payload["items"]))

    def test_watch_inbox_item_matches_bootstrap_signal_identity(self) -> None:
        response = self.client.get("/internal/watch/inbox")
        item = response.json()["items"][0]

        self.assertEqual(BOOTSTRAP_SIGNAL_ID, item["signal_id"])
        self.assertEqual(consistency_tuple(BOOTSTRAP_INBOX_ITEM), consistency_tuple(item))
        for field in CONSISTENCY_FIELDS:
            self.assertEqual(BOOTSTRAP_INBOX_ITEM[field], item[field])


if __name__ == "__main__":
    unittest.main()
