from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from tests.support.stable_connector_probe import reset_watch_ephemeral_stores
from tests.support.watch_app_loader import load_watch_app, restore_app_modules
from tests.support.watch_db import isolate_watch_db


class WatchSignalAcknowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_watch_db(self)
        watch_app, self._watch_modules = load_watch_app()
        reset_watch_ephemeral_stores()
        self.client = TestClient(watch_app)
        self.addCleanup(self.client.close)

    def tearDown(self) -> None:
        restore_app_modules(self._watch_modules)

    def test_acknowledge_signal_removes_items_from_inbox(self) -> None:
        before = self.client.get("/internal/watch/inbox").json()
        self.assertGreater(before["count"], 0)
        signal_ids = [item["signal_id"] for item in before["items"]]

        response = self.client.post(
            "/internal/watch/commands",
            json={
                "command_type": "acknowledge_signal",
                "target_type": "signal",
                "requested_by": "test",
                "payload": {"signal_ids": signal_ids},
            },
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload["accepted"])
        self.assertEqual("completed", payload["status"])
        self.assertEqual(len(signal_ids), payload["receipt"]["result"]["count"])

        after = self.client.get("/internal/watch/inbox").json()
        self.assertEqual(0, after["count"])
        self.assertEqual([], after["items"])

    def test_acknowledge_signal_is_idempotent(self) -> None:
        signal_ids = [
            item["signal_id"] for item in self.client.get("/internal/watch/inbox").json()["items"]
        ]
        body = {
            "command_type": "acknowledge_signal",
            "payload": {"signal_ids": signal_ids},
            "requested_by": "test",
        }
        first = self.client.post("/internal/watch/commands", json=body)
        second = self.client.post("/internal/watch/commands", json=body)
        self.assertEqual(200, first.status_code)
        self.assertEqual(200, second.status_code)
        self.assertEqual(0, self.client.get("/internal/watch/inbox").json()["count"])


if __name__ == "__main__":
    unittest.main()
