"""P-D1 watch SQLite persistence parity tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.stable_connector_probe import reset_watch_ephemeral_stores
from tests.support.watch_app_loader import load_watch_app, restore_app_modules
from tests.support.watch_db import isolate_watch_db

REPO_ROOT = Path(__file__).resolve().parents[1]


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


class ParityD1WatchPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db_path = isolate_watch_db(self)
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

    def test_default_verify_wiring_includes_parity_d1_tests(self) -> None:
        package = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
        verify_script = package["scripts"]["verify:contracts"]
        self.assertIn("tests.test_parity_d1_watch_persistence", verify_script)

    def test_commands_events_receipts_survive_connection_restart(self) -> None:
        response = self.client.post(
            "/internal/watch/commands",
            json={
                "command_type": "reprobe_connector",
                "target_type": "connector",
                "target_id": "control_plane",
                "requested_by": "parity-d1",
            },
        )
        self.assertEqual(200, response.status_code)
        command_id = response.json()["command_id"]

        self.client.get("/internal/watch/inbox")
        receipts_before = self.client.get("/internal/watch/delivery/receipts?limit=20").json()
        events_before = self.client.get("/internal/watch/events?limit=20").json()
        self.assertGreaterEqual(receipts_before["count"], 1)
        self.assertGreaterEqual(events_before["count"], 1)

        self.client.close()

        from app.persistence import watch_store_sqlite  # noqa: WPS433

        connection = watch_store_sqlite.connect(self.db_path)
        try:
            command_count = connection.execute("SELECT COUNT(*) FROM watch_commands").fetchone()[0]
            event_count = connection.execute("SELECT COUNT(*) FROM watch_events").fetchone()[0]
            receipt_count = connection.execute(
                "SELECT COUNT(*) FROM watch_delivery_receipts"
            ).fetchone()[0]
        finally:
            connection.close()

        restore_app_modules(self._watch_modules)

        self.assertGreaterEqual(int(command_count), 1)
        self.assertGreaterEqual(int(event_count), 1)
        self.assertGreaterEqual(int(receipt_count), 1)

        watch_app, self._watch_modules = load_watch_app()
        restarted = TestClient(watch_app)
        self.addCleanup(restarted.close)

        show_response = restarted.get(f"/internal/watch/commands/{command_id}")
        self.assertEqual(200, show_response.status_code)
        self.assertEqual("completed", show_response.json()["status"])

        receipts_after = restarted.get("/internal/watch/delivery/receipts?limit=20").json()
        events_after = restarted.get("/internal/watch/events?limit=20").json()
        self.assertEqual(receipts_before["count"], receipts_after["count"])
        self.assertGreaterEqual(events_after["count"], events_before["count"])

    def test_reset_store_clears_sqlite_tables(self) -> None:
        self.client.post(
            "/internal/watch/commands",
            json={"command_type": "refresh_summary", "requested_by": "parity-d1"},
        )
        from app.persistence import watch_store_sqlite  # noqa: WPS433

        connection = watch_store_sqlite.connect(self.db_path)
        try:
            self.assertGreater(int(connection.execute("SELECT COUNT(*) FROM watch_commands").fetchone()[0]), 0)
        finally:
            connection.close()

        reset_watch_ephemeral_stores()
        connection = watch_store_sqlite.connect(self.db_path)
        try:
            self.assertEqual(0, int(connection.execute("SELECT COUNT(*) FROM watch_commands").fetchone()[0]))
            self.assertEqual(0, int(connection.execute("SELECT COUNT(*) FROM watch_events").fetchone()[0]))
            self.assertEqual(
                0,
                int(connection.execute("SELECT COUNT(*) FROM watch_delivery_receipts").fetchone()[0]),
            )
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
