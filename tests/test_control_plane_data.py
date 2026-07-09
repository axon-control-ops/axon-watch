from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402


class ControlPlaneDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    @patch("app.data.snapshot.fetch_watch_data_snapshot")
    @patch("app.persistence.run_store.list_runs")
    @patch("app.persistence.chat_store.list_threads")
    @patch("app.persistence.chat_store.list_recent_messages")
    @patch("app.persistence.chat_store.count_threads")
    @patch("app.persistence.chat_store.count_messages")
    @patch("app.persistence.handoff_store.list_recent_handoffs")
    @patch("app.persistence.handoff_store.count_handoffs")
    def test_data_snapshot_route_returns_merged_tables(
        self,
        mock_handoff_count,
        mock_handoffs,
        mock_message_count,
        mock_thread_count,
        mock_messages,
        mock_threads,
        mock_runs,
        mock_watch_snapshot,
    ) -> None:
        mock_runs.return_value = [
            {
                "run_id": "run-1",
                "workspace_id": "ws-1",
                "lane_id": "lane-a",
                "mode": "agent",
                "status": "running",
                "phase": "execute",
                "summary": "Test run",
                "detail": "",
                "started_at": "2026-07-06T05:00:00Z",
                "updated_at": "2026-07-06T05:01:00Z",
                "ended_at": "",
                "can_stop": True,
                "can_resume": False,
                "can_approve": False,
                "can_review": False,
                "current_step": "",
                "history_ref": "hist-1",
            },
        ]
        mock_threads.return_value = [
            {
                "thread_id": "thread-1",
                "workspace_id": "ws-1",
                "run_id": "run-1",
                "created_at": "2026-07-06T05:00:00Z",
                "updated_at": "2026-07-06T05:01:00Z",
            },
        ]
        mock_messages.return_value = [
            {
                "message_id": "msg-1",
                "thread_id": "thread-1",
                "workspace_id": "ws-1",
                "run_id": "run-1",
                "role": "user",
                "content": "hello",
                "created_at": "2026-07-06T05:00:30Z",
            },
        ]
        mock_handoffs.return_value = []
        mock_thread_count.return_value = 1
        mock_message_count.return_value = 1
        mock_handoff_count.return_value = 0
        mock_watch_snapshot.return_value = {
            "updated_at": "2026-07-06T05:02:00Z",
            "tables": {
                "commands": {"total": 0, "count": 0, "items": []},
                "events": {"total": 0, "count": 0, "items": []},
                "receipts": {"total": 0, "count": 0, "items": []},
                "suppressions": {"total": 0, "count": 0, "items": []},
            },
        }

        response = self.client.get("/api/data/snapshot")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(1, payload["data"]["control_plane"]["runs"]["total"])
        self.assertEqual(1, payload["data"]["control_plane"]["chat_threads"]["total"])
        self.assertIn("commands", payload["data"]["watch"])

    @patch("app.routes.data.get_data_export")
    def test_data_export_route_sets_attachment_header(self, mock_export) -> None:
        mock_export.return_value = {"data": {"updated_at": "2026-07-06T05:02:00Z"}}
        response = self.client.get("/api/data/export")
        self.assertEqual(200, response.status_code)
        self.assertIn(
            'attachment; filename="axon-operator-data-export.json"',
            response.headers.get("content-disposition", ""),
        )


if __name__ == "__main__":
    unittest.main()
