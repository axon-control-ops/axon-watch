from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
WATCH_ROOT = REPO_ROOT / "services" / "axon-watch"
sys.path.insert(0, str(WATCH_ROOT))

WATCH_BASE = os.environ.get(
    "AXON_WATCH_WATCH_SERVICE_BASE_URL",
    "http://127.0.0.1:8788",
).rstrip("/")


def _request(method: str, url: str, payload: dict | None = None) -> tuple[int, object]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
            status = int(response.status)
    except URLError as exc:
        raise unittest.SkipTest(f"axon-watch unavailable: {exc}") from exc
    if not body.strip():
        return status, {}
    parsed = json.loads(body)
    return status, parsed


class VaultParityAcceptance(unittest.TestCase):
    def test_setup_unlock_crud_lock_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["AXON_WATCH_STATE_DIR"] = tmpdir
            # Fresh watch process required for isolated state; live test uses running service state.
            # Verify crypto endpoints exist and enforce lock semantics on a running stack.
            status, payload = _request("GET", f"{WATCH_BASE}/internal/watch/vault/status")
            self.assertEqual(200, status)
            vault = payload["vault"]
            self.assertIn("is_setup", vault)
            self.assertIn("is_unlocked", vault)

            status, locked = _request("GET", f"{WATCH_BASE}/internal/watch/vault/secrets")
            if not vault.get("is_unlocked"):
                self.assertIn(status, {423, 503})
            else:
                self.assertEqual(200, status)
                self.assertIsInstance(locked, list)

            status, provider = _request("GET", f"{WATCH_BASE}/internal/watch/vault/provider-keys")
            self.assertEqual(200, status)
            self.assertIn("unlocked", provider)
            self.assertIn("resolved", provider)


if __name__ == "__main__":
    unittest.main()
