"""TEST-6 live acceptance for KAIRO watch_rule metadata on inbox signals.

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
class Test6KairoWatchRulesAcceptance(unittest.TestCase):
    def test_inbox_items_include_watch_rule(self) -> None:
        status, payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/inbox")
        self.assertEqual(200, status)
        bootstrap = next(
            row for row in payload["items"] if row["signal_id"] == "signal_watch_bootstrap_ready"
        )
        rule = bootstrap["watch_rule"]
        self.assertIn(rule["mode"], {"observe", "advise", "approval", "execute"})
        self.assertTrue(rule["reason"])
        self.assertIsInstance(rule["interrupts"], bool)


if __name__ == "__main__":
    unittest.main()
