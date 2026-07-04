from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import chat_store  # noqa: E402
from app.persistence import run_store  # noqa: E402


class ControlPlaneChatTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        chat_store.reset_store()
        self.addCleanup(chat_store.reset_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_post_chat_message_creates_thread_and_ack(self) -> None:
        response = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_alpha",
                "content": " inspect runtime ",
            },
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload["thread_id"].startswith("thread_"))
        self.assertEqual(3, len(payload["messages"]))
        self.assertEqual("operator", payload["messages"][0]["role"])
        self.assertEqual("inspect runtime", payload["messages"][0]["content"])
        self.assertEqual("system", payload["messages"][1]["role"])
        self.assertEqual("agent", payload["messages"][2]["role"])
        self.assertTrue(payload["run_id"].startswith("run_"))
        self.assertTrue(payload["dispatched"])
        self.assertEqual(payload["run_id"], payload["run"]["run_id"])
        self.assertIn("dispatched", payload["messages"][1]["content"])
        self.assertEqual("review_ready", payload["run"]["phase"])
        self.assertIn("inspect runtime", payload["messages"][2]["content"])
        self.assertIsNotNone(run_store.get_run(payload["run_id"]))

    def test_post_chat_message_appends_to_existing_thread(self) -> None:
        first = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_alpha",
                "content": "first command",
            },
        ).json()
        thread_id = first["thread_id"]

        second = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_alpha",
                "content": "second command",
                "thread_id": thread_id,
            },
        )

        self.assertEqual(200, second.status_code)
        self.assertEqual(thread_id, second.json()["thread_id"])

        history = self.client.get(f"/api/chat/threads/{thread_id}/history")
        self.assertEqual(200, history.status_code)
        self.assertEqual(6, history.json()["count"])

    def test_get_chat_thread_and_history(self) -> None:
        created = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_alpha",
                "content": "hello",
            },
        ).json()
        thread_id = created["thread_id"]
        run_id = created["run_id"]

        thread = self.client.get(f"/api/chat/threads/{thread_id}")
        self.assertEqual(200, thread.status_code)
        self.assertEqual("workspace_alpha", thread.json()["workspace_id"])
        self.assertEqual(run_id, thread.json()["run_id"])

        history = self.client.get(f"/api/chat/threads/{thread_id}/history")
        self.assertEqual(200, history.status_code)
        history_payload = history.json()
        self.assertEqual(thread_id, history_payload["thread_id"])
        self.assertEqual(3, history_payload["count"])
        self.assertEqual(
            {"message_id", "thread_id", "run_id", "workspace_id", "role", "content", "created_at"},
            set(history_payload["items"][0]),
        )

    def test_post_chat_message_rejects_empty_content(self) -> None:
        response = self.client.post(
            "/api/chat/messages",
            json={"workspace_id": "workspace_alpha", "content": "   "},
        )
        self.assertEqual(400, response.status_code)

    def test_post_chat_message_rejects_unknown_workspace(self) -> None:
        response = self.client.post(
            "/api/chat/messages",
            json={"workspace_id": "workspace_missing", "content": "hello"},
        )
        self.assertEqual(400, response.status_code)

    def test_get_missing_thread_returns_404(self) -> None:
        response = self.client.get("/api/chat/threads/thread_missing/history")
        self.assertEqual(404, response.status_code)

    def test_get_workspace_chat_thread_returns_latest_thread(self) -> None:
        first = self.client.post(
            "/api/chat/messages",
            json={"workspace_id": "workspace_alpha", "content": "first thread"},
        ).json()
        second = self.client.post(
            "/api/chat/messages",
            json={"workspace_id": "workspace_alpha", "content": "second thread"},
        ).json()

        response = self.client.get("/api/workspaces/workspace_alpha/chat/thread")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(second["thread_id"], payload["thread_id"])
        self.assertEqual("workspace_alpha", payload["workspace_id"])
        self.assertIn("updated_at", payload)
        self.assertNotEqual(first["thread_id"], payload["thread_id"])

    def test_get_workspace_chat_thread_returns_empty_snapshot_when_no_thread(self) -> None:
        response = self.client.get("/api/workspaces/workspace_alpha/chat/thread")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertIsNone(payload["thread_id"])
        self.assertEqual("workspace_alpha", payload["workspace_id"])
        self.assertIsNone(payload["run_id"])
        self.assertIsNone(payload["updated_at"])

    def test_get_workspace_chat_thread_returns_404_for_unknown_workspace(self) -> None:
        response = self.client.get("/api/workspaces/workspace_missing/chat/thread")
        self.assertEqual(404, response.status_code)

    def test_post_chat_message_attaches_to_active_run(self) -> None:
        active_run = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Existing active run",
            },
        ).json()

        response = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_alpha",
                "content": "add context to active run",
                "run_id": active_run["run_id"],
            },
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertFalse(payload["dispatched"])
        self.assertEqual(active_run["run_id"], payload["run_id"])
        self.assertEqual("executing", payload["run"]["phase"])
        self.assertEqual(3, len(payload["messages"]))
        self.assertEqual("agent", payload["messages"][2]["role"])
        self.assertIn("linked", payload["messages"][1]["content"])

    def test_post_chat_message_dispatches_new_run_when_existing_run_is_terminal(self) -> None:
        completed_run = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Completed run",
            },
        ).json()
        self.client.post(f"/api/runs/{completed_run['run_id']}/complete")

        response = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_alpha",
                "content": "start fresh work",
                "run_id": completed_run["run_id"],
            },
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload["dispatched"])
        self.assertNotEqual(completed_run["run_id"], payload["run_id"])
        self.assertIn("dispatched", payload["messages"][1]["content"])
