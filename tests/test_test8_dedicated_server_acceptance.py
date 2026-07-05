"""TEST-8 live acceptance for dedicated-server readiness signals."""

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


def _request(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def _stack_available() -> bool:
    status, _ = _request(f"{CONTROL_PLANE_BASE}/api/health")
    return status == 200


@unittest.skipUnless(_stack_available(), "dev stack not running on control-plane base URL")
class Test8DedicatedServerAcceptance(unittest.TestCase):
    def test_control_plane_readiness_reports_configured_state(self) -> None:
        status, payload = _request(f"{CONTROL_PLANE_BASE}/api/readiness")
        self.assertEqual(200, status)
        self.assertIn(payload.get("mode"), {"bootstrap", "dedicated"})
        self.assertTrue(str(payload.get("watch_base_url", "")).startswith("http"))
        self.assertTrue(str(payload.get("state_dir", "")))

    def test_watch_readiness_reports_state_dir(self) -> None:
        status, payload = _request(f"{WATCH_BASE}/internal/watch/readiness")
        self.assertEqual(200, status)
        self.assertTrue(str(payload.get("state_dir", "")))


if __name__ == "__main__":
    unittest.main()
