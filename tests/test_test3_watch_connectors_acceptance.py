"""TEST-3 live acceptance for watch connector probes and runtime projection.

Requires `./scripts/dev/up.sh` (ports 4173 / 8787 / 8788).

Run:
  python3 -m unittest tests.test_test3_watch_connectors_acceptance
  ./scripts/verify/test3-watch-connectors.sh
"""

from __future__ import annotations

import json
import os
import time
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


def _request(method: str, url: str) -> tuple[int, dict | list | str]:
    req = urllib.request.Request(url, method=method)
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
class Test3WatchConnectorsAcceptance(unittest.TestCase):
    def test_watch_connectors_probe_required_services(self) -> None:
        status, payload = _request("GET", f"{WATCH_BASE}/internal/watch/connectors")
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)
        items = payload.get("items", [])
        self.assertIsInstance(items, list)
        by_id = {item["connector_id"]: item for item in items}
        self.assertIn("control_plane", by_id)
        self.assertIn("console_web", by_id)
        self.assertEqual("ok", by_id["control_plane"]["status"])
        self.assertEqual("ok", by_id["console_web"]["status"])
        self.assertEqual(0, payload["summary"]["required_unavailable"])

    def test_runtime_summary_projects_connector_counts(self) -> None:
        deadline = time.monotonic() + 20.0
        last_payload: dict | list | str = {}
        status = 0
        while time.monotonic() < deadline:
            status, payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/runtime/summary")
            last_payload = payload
            if status == 200 and isinstance(payload, dict):
                connectors = payload.get("connectors", {})
                if (
                    isinstance(connectors, dict)
                    and int(connectors.get("configured", 0)) >= 2
                    and int(connectors.get("ok", 0)) >= 2
                    and int(connectors.get("required_unavailable", 0)) == 0
                ):
                    return
            time.sleep(0.5)

        self.assertEqual(200, status)
        self.assertIsInstance(last_payload, dict)
        connectors = last_payload.get("connectors", {})
        self.assertGreaterEqual(connectors.get("configured", 0), 2)
        self.assertGreaterEqual(connectors.get("ok", 0), 2)
        self.assertEqual(0, connectors.get("required_unavailable"))

    def test_control_plane_connectors_endpoint(self) -> None:
        status, payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/connectors")
        self.assertEqual(200, status)
        self.assertGreaterEqual(payload.get("count", 0), 2)


if __name__ == "__main__":
    unittest.main()
