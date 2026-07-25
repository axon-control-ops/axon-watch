from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "control-plane"))

CONTROL_PLANE_BASE = os.environ.get(
    "AXON_WATCH_CONTROL_PLANE_BASE_URL",
    "http://127.0.0.1:8787",
).rstrip("/")


def _request(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            status = int(response.status)
    except URLError as exc:
        raise unittest.SkipTest(f"control-plane unavailable: {exc}") from exc
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise AssertionError("response was not an object")
    return status, parsed


class Test14VaultSurfaceAcceptance(unittest.TestCase):
    def test_vault_status_exposes_consumer_map_without_secret_values(self) -> None:
        status, payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/vault/status")
        self.assertEqual(200, status)
        vault = payload.get("vault")
        self.assertIsInstance(vault, dict)
        self.assertIn("available_keys", vault)
        self.assertIn("consumers", vault)
        self.assertIn("is_setup", vault)
        self.assertIn("is_unlocked", vault)
        self.assertNotIn("secrets", vault)
        consumers = vault.get("consumers")
        self.assertIsInstance(consumers, list)
        if consumers:
            first = consumers[0]
            self.assertIn("status", first)
            self.assertIn("vault_surface", first)
            self.assertEqual("/vault", first["vault_surface"])


if __name__ == "__main__":
    unittest.main()
