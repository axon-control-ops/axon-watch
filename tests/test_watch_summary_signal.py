from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from tests.support.summary_degraded_signal_fixture import (
    CONSISTENCY_FIELDS,
    SUMMARY_DEGRADED_INBOX_ITEM,
    SUMMARY_DEGRADED_SIGNAL_EVENT_STATIC,
    SUMMARY_DEGRADED_SIGNAL_ID,
    consistency_tuple,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "packages" / "shared-types" / "fixtures"
WATCH_ROOT = REPO_ROOT / "services" / "axon-watch"


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


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
    from app.signals.summary_degraded_signal import summary_degraded_signal_event  # noqa: WPS433

    return watch_app, summary_degraded_signal_event, cached


def _restore_modules(cached: dict[str, object]) -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    sys.modules.update(cached)


_STATIC_EVENT_FIELDS = (
    "event_id",
    "signal_id",
    "event_type",
    "source",
    "workspace_id",
    "project_id",
    "severity",
    "status",
    "title",
    "body",
    "summary",
    "dedupe_key",
    "action_type",
    "action_payload",
    "correlation_ref",
    "delivery_state",
    "meta",
)


class WatchSummarySignalTests(unittest.TestCase):
    def setUp(self) -> None:
        self._cached_modules: dict[str, object] = {}
        watch_app, self.summary_degraded_signal_event, self._cached_modules = _load_watch_app()
        self.client = TestClient(watch_app)

    def tearDown(self) -> None:
        _restore_modules(self._cached_modules)

    def test_watch_inbox_ranks_summary_degraded_above_bootstrap(self) -> None:
        response = self.client.get("/internal/watch/inbox")

        self.assertEqual(200, response.status_code)
        items = response.json()["items"]
        self.assertEqual(2, len(items))
        self.assertEqual(SUMMARY_DEGRADED_SIGNAL_ID, items[0]["signal_id"])
        self.assertEqual("signal_watch_bootstrap_ready", items[1]["signal_id"])

    def test_watch_inbox_item_matches_summary_degraded_contract_fixture(self) -> None:
        response = self.client.get("/internal/watch/inbox")
        item = next(
            row for row in response.json()["items"] if row["signal_id"] == SUMMARY_DEGRADED_SIGNAL_ID
        )
        fixture_item = _load_fixture("inbox-item.example.json")

        self.assertEqual(consistency_tuple(fixture_item), consistency_tuple(item))
        for field in CONSISTENCY_FIELDS:
            self.assertEqual(fixture_item[field], item[field])
        self.assertEqual(SUMMARY_DEGRADED_INBOX_ITEM["title"], item["title"])
        self.assertEqual(SUMMARY_DEGRADED_INBOX_ITEM["summary"], item["summary"])
        self.assertEqual(SUMMARY_DEGRADED_INBOX_ITEM["action_type"], item["action_type"])

    def test_summary_degraded_event_matches_signal_event_contract_fixture(self) -> None:
        event = self.summary_degraded_signal_event()
        fixture_event = _load_fixture("signal-event.example.json")

        for field in _STATIC_EVENT_FIELDS:
            self.assertEqual(fixture_event[field], event[field])
        self.assertEqual(SUMMARY_DEGRADED_SIGNAL_EVENT_STATIC["dedupe_key"], event["dedupe_key"])


if __name__ == "__main__":
    unittest.main()
