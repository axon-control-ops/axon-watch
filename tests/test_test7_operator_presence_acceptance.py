"""TEST-7 live acceptance for operator presence, spoken alerts, and mobile posture.

Requires `./scripts/dev/up.sh` (ports 4173 / 8787 / 8788).
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


def _request(method: str, url: str) -> tuple[int, dict]:
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def _stack_available() -> bool:
    status, _ = _request("GET", f"{CONTROL_PLANE_BASE}/api/health")
    return status == 200


@unittest.skipUnless(_stack_available(), "dev stack not running on control-plane base URL")
class Test7OperatorPresenceAcceptance(unittest.TestCase):
    def test_briefing_includes_operator_presence(self) -> None:
        status, payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/briefing")
        self.assertEqual(200, status)
        presence = payload["operator_presence"]
        self.assertTrue(presence["persona_voice_line"].startswith("KAIRO:"))
        self.assertIn(presence["presence_state"], {"idle", "observing", "alerting", "privacy_blocked"})
        self.assertTrue(presence["mobile"]["foreground_only"])

    def test_mobile_compact_query_flag(self) -> None:
        status, payload = _request(
            "GET",
            f"{CONTROL_PLANE_BASE}/api/briefing?viewport_compact=true",
        )
        self.assertEqual(200, status)
        self.assertTrue(payload["operator_presence"]["mobile"]["compact_layout"])


if __name__ == "__main__":
    unittest.main()
