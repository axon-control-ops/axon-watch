from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from tests.support.stable_connector_probe import (
    patch_stable_connector_probes,
    reset_watch_ephemeral_stores,
)
from tests.support.watch_app_loader import load_watch_app, restore_app_modules
from tests.support.watch_db import isolate_watch_db


class WatchDeliveryReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_watch_db(self)
        watch_app, self._watch_modules = load_watch_app()
        reset_watch_ephemeral_stores()
        self._connector_patch = patch_stable_connector_probes()
        self._connector_patch.start()
        self.addCleanup(self._connector_patch.stop)
        self.client = TestClient(watch_app)
        self.addCleanup(self.client.close)

    def tearDown(self) -> None:
        restore_app_modules(self._watch_modules)

    @staticmethod
    def _degraded_connectors() -> list[dict[str, object]]:
        from tests.support.stable_connector_probe import STABLE_OK_CONNECTOR_RECORDS

        return [
            {
                **record,
                "status": "unavailable" if record.get("required") else record.get("status"),
            }
            for record in STABLE_OK_CONNECTOR_RECORDS
        ]

    def test_inbox_high_signal_receives_delivery_receipts(self) -> None:
        # Force summary-degraded into the inbox by reporting required connectors as unavailable.
        from unittest.mock import patch

        degraded_connectors = self._degraded_connectors()
        with patch(
            "app.main.probe_all_connectors",
            return_value=degraded_connectors,
        ), patch(
            "app.connectors.summary.probe_all_connectors",
            return_value=degraded_connectors,
        ), patch(
            "app.watch_summary.probe_all_connectors",
            return_value=degraded_connectors,
        ):
            response = self.client.get("/internal/watch/inbox")
        self.assertEqual(200, response.status_code)
        items = response.json()["items"]
        degraded = next(
            row for row in items if row["signal_id"] == "signal_runtime_summary_degraded"
        )
        self.assertEqual("delivered", degraded["delivery_state"])
        self.assertGreaterEqual(int(degraded.get("delivery_receipt_count", 0)), 2)
        self.assertTrue(str(degraded.get("latest_receipt_id", "")).startswith("rcpt-"))

    def test_bootstrap_signal_skips_delivery(self) -> None:
        response = self.client.get("/internal/watch/inbox")
        items = response.json()["items"]
        bootstrap = next(
            row for row in items if row["signal_id"] == "signal_watch_bootstrap_ready"
        )
        self.assertEqual("not_required", bootstrap["delivery_state"])

    def test_delivery_receipts_index_returns_canonical_shape(self) -> None:
        from unittest.mock import patch

        degraded_connectors = self._degraded_connectors()
        with patch(
            "app.main.probe_all_connectors",
            return_value=degraded_connectors,
        ), patch(
            "app.connectors.summary.probe_all_connectors",
            return_value=degraded_connectors,
        ), patch(
            "app.watch_summary.probe_all_connectors",
            return_value=degraded_connectors,
        ):
            self.client.get("/internal/watch/inbox")
        response = self.client.get("/internal/watch/delivery/receipts?limit=10")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertGreaterEqual(payload["count"], 2)
        receipt = payload["items"][0]
        self.assertEqual(
            {
                "receipt_id",
                "signal_id",
                "event_id",
                "channel",
                "attempted_at",
                "result",
                "error",
                "policy_reason",
            },
            set(receipt),
        )
        self.assertEqual("succeeded", receipt["result"])

    def test_delivery_emits_lifecycle_events(self) -> None:
        from unittest.mock import patch

        degraded_connectors = self._degraded_connectors()
        with patch(
            "app.main.probe_all_connectors",
            return_value=degraded_connectors,
        ), patch(
            "app.connectors.summary.probe_all_connectors",
            return_value=degraded_connectors,
        ), patch(
            "app.watch_summary.probe_all_connectors",
            return_value=degraded_connectors,
        ):
            self.client.get("/internal/watch/inbox")
        response = self.client.get("/internal/watch/events?limit=20")
        event_types = {item["event_type"] for item in response.json()["items"]}
        self.assertIn("delivery_attempted", event_types)
        self.assertIn("delivery_succeeded", event_types)

    def test_summary_observation_includes_delivery_counts(self) -> None:
        from unittest.mock import patch

        degraded_connectors = self._degraded_connectors()
        with patch(
            "app.main.probe_all_connectors",
            return_value=degraded_connectors,
        ), patch(
            "app.connectors.summary.probe_all_connectors",
            return_value=degraded_connectors,
        ), patch(
            "app.watch_summary.probe_all_connectors",
            return_value=degraded_connectors,
        ):
            self.client.get("/internal/watch/inbox")
        response = self.client.get("/internal/watch/summary")
        observation = response.json()["observation"]
        self.assertGreaterEqual(observation["receipts_count"], 2)
        self.assertTrue(observation["last_receipt_at"])
        self.assertEqual("succeeded", observation["last_receipt_result"])

    def test_repeated_inbox_fetch_does_not_duplicate_receipts(self) -> None:
        self.client.get("/internal/watch/inbox")
        first = self.client.get("/internal/watch/delivery/receipts?limit=50").json()["count"]
        self.client.get("/internal/watch/inbox")
        second = self.client.get("/internal/watch/delivery/receipts?limit=50").json()["count"]
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
