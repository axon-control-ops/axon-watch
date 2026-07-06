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
WATCH_BASE = os.environ.get(
    "AXON_WATCH_WATCH_SERVICE_BASE_URL",
    "http://127.0.0.1:8788",
).rstrip("/")


def _request(method: str, url: str) -> tuple[int, dict]:
    request = Request(url, method=method, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            status = int(response.status)
    except URLError as exc:
        raise unittest.SkipTest(f"service unavailable: {exc}") from exc
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise AssertionError("response was not an object")
    return status, parsed


class Test15OperatorDataAcceptance(unittest.TestCase):
    def test_watch_data_snapshot_exposes_read_only_tables(self) -> None:
        status, payload = _request("GET", f"{WATCH_BASE}/internal/watch/data/snapshot")
        self.assertEqual(200, status)
        data = payload.get("data")
        self.assertIsInstance(data, dict)
        tables = data.get("tables")
        self.assertIsInstance(tables, dict)
        for table_name in ("commands", "events", "receipts", "suppressions"):
            self.assertIn(table_name, tables)
            table = tables[table_name]
            self.assertIn("total", table)
            self.assertIn("items", table)

    def test_control_plane_data_snapshot_merges_control_plane_and_watch(self) -> None:
        status, payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/data/snapshot")
        self.assertEqual(200, status)
        data = payload.get("data")
        self.assertIsInstance(data, dict)
        control_plane = data.get("control_plane")
        self.assertIsInstance(control_plane, dict)
        for table_name in ("runs", "chat_threads", "chat_messages", "handoffs"):
            self.assertIn(table_name, control_plane)
        watch = data.get("watch")
        self.assertIsInstance(watch, dict)
        self.assertIn("commands", watch)


if __name__ == "__main__":
    unittest.main()
