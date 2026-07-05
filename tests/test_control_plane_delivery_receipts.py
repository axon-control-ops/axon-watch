from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402


class ControlPlaneDeliveryReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        from app.persistence import run_store

        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_delivery_receipts_endpoint_proxies_watch_payload(self) -> None:
        watch_payload = {
            "items": [
                {
                    "receipt_id": "rcpt-test-001",
                    "signal_id": "signal_runtime_summary_degraded",
                    "event_id": "event-delivery-signal_runtime_summary_degraded",
                    "channel": "inbox",
                    "attempted_at": "2026-07-05T08:00:00Z",
                    "result": "succeeded",
                    "error": "",
                    "policy_reason": "inbox_projection_available",
                }
            ],
            "count": 1,
            "next_cursor": "",
            "updated_at": "2026-07-05T08:00:00Z",
        }
        with patch(
            "app.main.fetch_watch_delivery_receipts",
            return_value=watch_payload,
        ):
            response = self.client.get("/api/delivery/receipts")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(1, payload["count"])
        self.assertEqual("rcpt-test-001", payload["items"][0]["receipt_id"])

    def test_inbox_projection_includes_delivery_state(self) -> None:
        watch_inbox = {
            "items": [
                {
                    "signal_id": "signal_runtime_summary_degraded",
                    "workspace_id": "workspace_alpha",
                    "title": "Watch summary degraded",
                    "summary": "Watch summary is degraded.",
                    "severity": "high",
                    "status": "open",
                    "source": "watch",
                    "created_at": "2026-07-03T15:01:00Z",
                    "updated_at": "2026-07-03T15:02:00Z",
                    "action_type": "open_dashboard",
                    "delivery_state": "delivered",
                    "latest_receipt_id": "rcpt-test-001",
                }
            ],
            "count": 1,
            "updated_at": "2026-07-03T15:02:00Z",
        }
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=watch_inbox,
        ):
            response = self.client.get("/api/inbox")

        item = response.json()["items"][0]
        self.assertEqual("delivered", item["delivery_state"])
        self.assertEqual("rcpt-test-001", item["latest_receipt_id"])


if __name__ == "__main__":
    unittest.main()
