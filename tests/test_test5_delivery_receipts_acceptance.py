"""TEST-5 live acceptance for delivery receipts on operator attention signals.

Requires `./scripts/dev/up.sh` (ports 4173 / 8787 / 8788).

Run:
  python3 -m unittest tests.test_test5_delivery_receipts_acceptance
  ./scripts/verify/test5-delivery-receipts.sh
"""

from __future__ import annotations

import json
import os
import unittest
import urllib.error
import urllib.request

CONTROL_PLANE_BASE = os.environ.get(
    "AXON_WATCH_CONTROL_PLANE_BASE",
    "http://127.0.0.1:8787",
)
WATCH_BASE = os.environ.get(
    "AXON_WATCH_WATCH_SERVICE_BASE",
    "http://127.0.0.1:8788",
)


def _request(
    method: str,
    url: str,
    body: dict | None = None,
) -> tuple[int, dict | list | str]:
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read().decode()
            if not raw:
                return response.status, {}
            try:
                return response.status, json.loads(raw)
            except json.JSONDecodeError:
                return response.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def _stack_available() -> bool:
    status, _ = _request("GET", f"{CONTROL_PLANE_BASE}/api/health")
    return status == 200


@unittest.skipUnless(_stack_available(), "dev stack not running on control-plane base URL")
class Test5DeliveryReceiptsAcceptance(unittest.TestCase):
    def test_inbox_high_signal_has_delivery_state(self) -> None:
        status, payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/inbox")
        self.assertEqual(200, status)
        items = payload["items"] if isinstance(payload, dict) else []
        bootstrap = next(
            (row for row in items if row.get("signal_id") == "signal_watch_bootstrap_ready"),
            None,
        )
        self.assertIsNotNone(bootstrap)
        self.assertEqual("delivered", bootstrap.get("delivery_state"))
        self.assertTrue(str(bootstrap.get("latest_receipt_id", "")).startswith("rcpt-"))

    def test_delivery_receipts_available_via_control_plane(self) -> None:
        _request("GET", f"{WATCH_BASE}/internal/watch/inbox")
        status, payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/delivery/receipts?limit=10")
        self.assertEqual(200, status)
        self.assertGreaterEqual(payload.get("count", 0), 1)
        channels = {item.get("channel") for item in payload.get("items", [])}
        self.assertIn("inbox", channels)

    def test_watch_summary_observation_includes_receipt_counts(self) -> None:
        status, payload = _request("GET", f"{WATCH_BASE}/internal/watch/summary")
        self.assertEqual(200, status)
        observation = payload.get("observation", {})
        self.assertGreaterEqual(observation.get("receipts_count", 0), 1)


if __name__ == "__main__":
    unittest.main()
