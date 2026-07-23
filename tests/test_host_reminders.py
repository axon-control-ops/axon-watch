from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.host_context.reminders import (  # noqa: E402
    due_reminders,
    migrate_whatsapp_g42_reminder,
)
from app.main import app  # noqa: E402
from app.persistence import operator_memory_store, run_store  # noqa: E402


class HostReminderTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_due_reminder_surfaces_in_briefing(self) -> None:
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )
        created = operator_memory_store.create_memory(
            workspace_id="",
            scope="personal",
            kind="reminder",
            title="Ship desktop bridge",
            content="Finish host context APIs",
            source_refs=[],
            created_at=past,
            due_at=past,
            trigger="time",
            priority="high",
            status="open",
        )
        due = due_reminders(limit=5)
        self.assertTrue(any(item["memory_id"] == created["memory_id"] for item in due))

        briefing = self.client.get("/api/briefing")
        self.assertEqual(200, briefing.status_code)
        payload = briefing.json()
        self.assertIn("due_reminders", payload)
        self.assertTrue(
            any(item["memory_id"] == created["memory_id"] for item in payload["due_reminders"])
        )
        self.assertTrue(
            any(item["memory_id"] == created["memory_id"] for item in payload["memory_highlights"])
        )

    def test_snooze_and_dismiss(self) -> None:
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )
        created = self.client.post(
            "/api/host/reminders",
            json={
                "title": "Check canary",
                "content": "Verify OTA canary",
                "due_at": past,
                "priority": "normal",
            },
        )
        self.assertEqual(200, created.status_code)
        memory_id = created.json()["memory_id"]

        snoozed = self.client.patch(
            f"/api/host/reminders/{memory_id}",
            json={"status": "snoozed"},
        )
        self.assertEqual(200, snoozed.status_code)
        self.assertEqual("snoozed", snoozed.json()["status"])
        self.assertTrue(snoozed.json()["snoozed_until"])

        listed = self.client.get("/api/host/reminders", params={"due_only": True})
        self.assertFalse(any(item["memory_id"] == memory_id for item in listed.json()["items"]))

        dismissed = self.client.patch(
            f"/api/host/reminders/{memory_id}",
            json={"status": "dismissed", "dismiss_reason": "done"},
        )
        self.assertEqual("dismissed", dismissed.json()["status"])

    def test_whatsapp_g42_migration(self) -> None:
        operator_memory_store.create_memory(
            workspace_id="",
            scope="personal",
            kind="note",
            title="Revisit WhatsApp soft-cutover (G4.2)",
            content="WhatsApp soft-cutover parked",
            source_refs=[],
            created_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )
        migrated = migrate_whatsapp_g42_reminder(due_hours=1)
        self.assertIsNotNone(migrated)
        assert migrated is not None
        self.assertEqual("reminder", migrated["kind"])
        self.assertEqual("high", migrated["priority"])
        self.assertTrue(migrated["due_at"])

        via_api = self.client.post("/api/host/reminders/migrate-whatsapp-g42")
        self.assertEqual(200, via_api.status_code)
        self.assertTrue(via_api.json()["ok"])


if __name__ == "__main__":
    unittest.main()
