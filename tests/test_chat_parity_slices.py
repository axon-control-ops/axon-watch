"""Tests for chat attachments, thread listing, and terminal session registry."""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.persistence import attachment_store, chat_store
from app.terminal.session_registry import ensure_agent_session, list_sessions, reset_registry


class ChatParitySliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = os.path.join(
            self._tmpdir.name,
            "control-plane.sqlite3",
        )
        os.environ["AXON_WATCH_STATE_DIR"] = os.path.join(self._tmpdir.name, "state")
        chat_store.reset_store()
        reset_registry()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()
        reset_registry()

    def test_upload_attachment_and_send_with_message(self) -> None:
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
            b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        upload = self.client.post(
            "/api/chat/attachments",
            data={"workspace_id": "workspace_alpha"},
            files={"file": ("diagram.png", io.BytesIO(png_bytes), "image/png")},
        )
        self.assertEqual(200, upload.status_code)
        attachment_id = upload.json()["attachment_id"]

        with patch(
            "app.chat.service.generate_lane_b_result",
            return_value={
                "content": "I see the diagram.",
                "dispatched": True,
                "runtime_id": "cursor_local",
                "runtime_label": "Cursor CLI (local)",
                "reason": "",
            },
        ):
            response = self.client.post(
                "/api/chat/messages",
                json={
                    "workspace_id": "workspace_alpha",
                    "content": "Review this screenshot",
                    "composer_mode": "ask",
                    "attachment_ids": [attachment_id],
                },
            )
        self.assertEqual(200, response.status_code)
        thread_id = response.json()["thread_id"]
        history = self.client.get(f"/api/chat/threads/{thread_id}/history").json()
        operator = next(item for item in history["items"] if item["role"] == "operator")
        self.assertEqual(1, len(operator.get("attachments", [])))
        self.assertEqual(attachment_id, operator["attachments"][0]["attachment_id"])

    def test_image_attachment_route_uses_inline_disposition(self) -> None:
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
            b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        upload = self.client.post(
            "/api/chat/attachments",
            data={"workspace_id": "workspace_alpha"},
            files={"file": ("diagram.png", io.BytesIO(png_bytes), "image/png")},
        )
        self.assertEqual(200, upload.status_code)
        attachment_id = upload.json()["attachment_id"]

        response = self.client.get(f"/api/chat/attachments/{attachment_id}")
        self.assertEqual(200, response.status_code)
        self.assertEqual("image/png", response.headers.get("content-type"))
        self.assertIn("inline", response.headers.get("content-disposition", "").lower())

    def test_list_and_create_workspace_chat_threads(self) -> None:
        with patch(
            "app.chat.service.generate_lane_b_result",
            return_value={
                "content": "First thread",
                "dispatched": False,
                "runtime_id": "",
                "runtime_label": "",
                "reason": "",
            },
        ):
            first = self.client.post(
                "/api/chat/messages",
                json={
                    "workspace_id": "workspace_alpha",
                    "content": "First IDE prompt",
                    "composer_mode": "ask",
                },
            ).json()

        created = self.client.post(
            "/api/workspaces/workspace_alpha/chat/threads",
            json={"surface": "ide"},
        )
        self.assertEqual(200, created.status_code)
        self.assertNotEqual(first["thread_id"], created.json()["thread_id"])

        listed = self.client.get("/api/workspaces/workspace_alpha/chat/threads?surface=ide")
        self.assertEqual(200, listed.status_code)
        payload = listed.json()
        self.assertGreaterEqual(payload["count"], 2)
        previews = {item["thread_id"]: item["preview_label"] for item in payload["items"]}
        self.assertIn("First IDE prompt", previews[first["thread_id"]])

    def test_agent_terminal_session_is_provisioned_for_agent_turn(self) -> None:
        with patch(
            "app.chat.service._lane_b_streaming_enabled",
            return_value=False,
        ), patch(
            "app.chat.service.generate_lane_b_result",
            return_value={
                "content": "Agent done",
                "dispatched": True,
                "runtime_id": "cursor_local",
                "runtime_label": "Cursor CLI (local)",
                "reason": "",
            },
        ):
            response = self.client.post(
                "/api/chat/messages",
                json={
                    "workspace_id": "workspace_alpha",
                    "content": "Run tests",
                    "composer_mode": "agent",
                    "execution_access": "consultative",
                },
            )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertIn("agent_terminal_session", payload)
        session = payload["agent_terminal_session"]
        self.assertEqual("agent", session["role"])
        self.assertEqual("terminal-agent", session["session_id"])

        sessions = self.client.get("/api/workspaces/workspace_alpha/terminal/sessions")
        self.assertEqual(200, sessions.status_code)
        session_ids = {item["session_id"] for item in sessions.json()["items"]}
        self.assertIn(session["session_id"], session_ids)

    def test_terminal_session_registry_lists_operator_default(self) -> None:
        sessions = list_sessions("workspace_alpha")
        self.assertTrue(any(item.session_id == "terminal-operator" for item in sessions))
        agent = ensure_agent_session(workspace_id="workspace_alpha", run_id="run_deadbeef")
        self.assertEqual("agent", agent.role)
        self.assertEqual("terminal-agent", agent.session_id)
        again = ensure_agent_session(workspace_id="workspace_alpha", run_id="run_cafebabe")
        self.assertEqual(agent.session_id, again.session_id)
        self.assertEqual("run_cafebabe", again.run_id)


if __name__ == "__main__":
    unittest.main()
