"""TEST-4 live acceptance for watch command, event, and summary observation depth.

Requires `./scripts/dev/up.sh` (ports 4173 / 8787 / 8788).

Run:
  python3 -m unittest tests.test_test4_watch_command_event_acceptance
  ./scripts/verify/test4-watch-command-event-depth.sh
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
class Test4WatchCommandEventAcceptance(unittest.TestCase):
    def test_reprobe_connector_via_control_plane(self) -> None:
        status, payload = _request(
            "POST",
            f"{CONTROL_PLANE_BASE}/api/watch/commands",
            {
                "command_type": "reprobe_connector",
                "target_type": "connector",
                "target_id": "control_plane",
                "requested_by": "TEST-4",
            },
        )
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)
        self.assertEqual("completed", payload.get("status"))
        command_id = str(payload.get("command_id", ""))
        self.assertTrue(command_id.startswith("cmd-"))

        show_status, show_payload = _request(
            "GET",
            f"{CONTROL_PLANE_BASE}/api/watch/commands/{command_id}",
        )
        self.assertEqual(200, show_status)
        self.assertEqual("reprobe_connector", show_payload.get("command_type"))

        connectors_status, connectors_payload = _request(
            "GET",
            f"{CONTROL_PLANE_BASE}/api/connectors",
        )
        self.assertEqual(200, connectors_status)
        self.assertIsInstance(connectors_payload, dict)
        items = connectors_payload.get("items")
        self.assertIsInstance(items, list)
        by_id = {
            str(item.get("connector_id")): item
            for item in items
            if isinstance(item, dict)
        }
        control_plane = by_id.get("control_plane")
        self.assertIsInstance(control_plane, dict)
        assert isinstance(control_plane, dict)
        result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        expected_status = str(result.get("connector_status") or control_plane.get("status") or "")
        self.assertTrue(expected_status)
        self.assertEqual(expected_status, control_plane.get("status"))

    def test_watch_events_and_summary_observation(self) -> None:
        _request(
            "POST",
            f"{WATCH_BASE}/internal/watch/commands",
            {"command_type": "refresh_summary", "requested_by": "TEST-4"},
        )

        events_status, events_payload = _request(
            "GET",
            f"{CONTROL_PLANE_BASE}/api/watch/events?limit=10",
        )
        self.assertEqual(200, events_status)
        items = events_payload.get("items") if isinstance(events_payload, dict) else []
        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 1)
        event_types = {item.get("event_type") for item in items}
        self.assertIn("summary_refreshed", event_types)

        summary_status, summary_payload = _request(
            "GET",
            f"{WATCH_BASE}/internal/watch/summary",
        )
        self.assertEqual(200, summary_status)
        observation = summary_payload.get("observation")
        self.assertIsInstance(observation, dict)
        assert isinstance(observation, dict)
        self.assertGreaterEqual(observation.get("events_count", 0), 1)
        self.assertTrue(str(observation.get("last_command_status", "")).strip())


if __name__ == "__main__":
    unittest.main()
