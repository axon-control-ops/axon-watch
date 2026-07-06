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


def _request(method: str, url: str) -> tuple[int, dict]:
    request = Request(url, method=method, headers={"Accept": "application/json"})
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


class RuntimeVaultAcceptance(unittest.TestCase):
    def test_runtime_status_includes_vault_posture(self) -> None:
        status, payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/runtime/status")
        self.assertEqual(200, status)
        vault_runtime = payload.get("vault_runtime")
        self.assertIsInstance(vault_runtime, dict)
        self.assertIn("posture", vault_runtime)
        self.assertIn("unlocked", vault_runtime)
        self.assertIn("hint", vault_runtime)
        local = payload.get("local")
        self.assertIsInstance(local, list)
        if local:
            auth = local[0].get("auth")
            self.assertIsInstance(auth, dict)
            self.assertIn("message", auth)


if __name__ == "__main__":
    unittest.main()
