from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.stable_connector_probe import reset_watch_ephemeral_stores
from tests.support.watch_app_loader import load_watch_app, restore_app_modules


def _stable_probe_connector(definition, *, timeout_seconds: float = 0.75) -> dict[str, object]:
    return {
        "connector_id": definition.connector_id,
        "display_name": definition.display_name,
        "health_url": definition.health_url,
        "required": definition.required,
        "workspace_id": definition.workspace_id,
        "status": "ok",
        "detail": "reachable",
        "last_checked_at": "2026-07-05T08:00:00Z",
        "latency_ms": 1,
    }


class WatchCommandsAndEventsTests(unittest.TestCase):
    def setUp(self) -> None:
        watch_app, self._watch_modules = load_watch_app()
        reset_watch_ephemeral_stores()
        self._probe_patch = patch(
            "app.commands.executor.probe_connector",
            side_effect=_stable_probe_connector,
        )
        self._probe_patch.start()
        self.addCleanup(self._probe_patch.stop)
        self.client = TestClient(watch_app)
        self.addCleanup(self.client.close)

    def tearDown(self) -> None:
        restore_app_modules(self._watch_modules)

    def test_reprobe_connector_command_returns_completed_receipt(self) -> None:
        response = self.client.post(
            "/internal/watch/commands",
            json={
                "command_type": "reprobe_connector",
                "target_type": "connector",
                "target_id": "control_plane",
                "requested_by": "test",
            },
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload["accepted"])
        self.assertEqual("completed", payload["status"])
        self.assertTrue(str(payload["command_id"]).startswith("cmd-"))
        self.assertEqual("ok", payload["receipt"]["result"]["connector_status"])

    def test_refresh_summary_command_records_observation_on_summary(self) -> None:
        response = self.client.post(
            "/internal/watch/commands",
            json={"command_type": "refresh_summary", "requested_by": "test"},
        )
        self.assertEqual(200, response.status_code)
        command_id = response.json()["command_id"]

        show_response = self.client.get(f"/internal/watch/commands/{command_id}")
        self.assertEqual(200, show_response.status_code)
        self.assertEqual("completed", show_response.json()["status"])

        summary_response = self.client.get("/internal/watch/summary")
        observation = summary_response.json()["observation"]
        self.assertGreaterEqual(observation["events_count"], 3)
        self.assertEqual(command_id, observation["last_command_id"])
        self.assertEqual("completed", observation["last_command_status"])

    def test_events_index_returns_command_lifecycle_events(self) -> None:
        self.client.post(
            "/internal/watch/commands",
            json={
                "command_type": "reprobe_connector",
                "target_id": "console_web",
            },
        )
        response = self.client.get("/internal/watch/events?limit=10")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertGreaterEqual(payload["count"], 1)
        event_types = {item["event_type"] for item in payload["items"]}
        self.assertIn("connector_reprobed", event_types)
        self.assertIn("command_completed", event_types)

    def test_unsupported_command_type_returns_400(self) -> None:
        response = self.client.post(
            "/internal/watch/commands",
            json={"command_type": "acknowledge_signal", "target_id": "signal_x"},
        )
        self.assertEqual(400, response.status_code)


if __name__ == "__main__":
    unittest.main()
