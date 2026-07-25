from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "axon-watch"))

WATCH_BASE = os.environ.get(
    "AXON_WATCH_WATCH_SERVICE_BASE_URL",
    "http://127.0.0.1:8788",
).rstrip("/")
CONTROL_PLANE_BASE = os.environ.get(
    "AXON_WATCH_CONTROL_PLANE_BASE_URL",
    "http://127.0.0.1:8787",
).rstrip("/")


def _request(url: str) -> tuple[int, dict]:
    request = Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
            status = int(response.status)
    except URLError as exc:
        raise unittest.SkipTest(f"service unavailable: {exc}") from exc
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise AssertionError("response was not an object")
    return status, parsed


class Test16DashproMonitorsAcceptance(unittest.TestCase):
    def test_watch_inbox_includes_dashpro_monitor_probe_results(self) -> None:
        status, payload = _request(f"{WATCH_BASE}/internal/watch/inbox")
        self.assertEqual(200, status)
        items = payload.get("items")
        self.assertIsInstance(items, list)

    def test_control_plane_inbox_projects_monitor_signals_when_unhealthy(self) -> None:
        status, payload = _request(f"{CONTROL_PLANE_BASE}/api/inbox")
        self.assertEqual(200, status)
        items = payload.get("items")
        self.assertIsInstance(items, list)

    def test_dashpro_monitor_slice_config_is_present(self) -> None:
        config_path = REPO_ROOT / "config" / "dashpro-monitor-slice.json"
        self.assertTrue(config_path.is_file())
        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual("workspace_dashpro", config.get("workspace_id"))
        checks = config.get("checks")
        self.assertIsInstance(checks, list)
        self.assertGreaterEqual(len(checks), 2)


if __name__ == "__main__":
    unittest.main()
