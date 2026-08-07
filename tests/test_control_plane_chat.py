from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.auth.rate_limit import reset_rate_limit_state_for_tests  # noqa: E402
from app.main import app  # noqa: E402
from app.kairo.turn_memory import clear_memory_for_tests, remember_entities, remember_turn  # noqa: E402
from app.persistence import chat_store  # noqa: E402
from app.persistence import run_store  # noqa: E402


class ControlPlaneChatTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.streaming_env = patch.dict(
            os.environ,
            {"AXON_WATCH_LANE_B_STREAMING": "0"},
            clear=False,
        )
        self.streaming_env.start()
        self.addCleanup(self.streaming_env.stop)
        chat_store.reset_store()
        self.addCleanup(chat_store.reset_store)
        clear_memory_for_tests()
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
        self.assertIn("Executed", payload["messages"][2]["content"])
        self.assertIn("unsupported", payload["messages"][2]["content"])
        self.assertIsNotNone(run_store.get_run(payload["run_id"]))

    def test_post_chat_message_resume_from_review_resumes_existing_run(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Awaiting follow-up",
            },
        ).json()
        self.client.post(f"/api/runs/{created['run_id']}/review-ready")

        response = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_alpha",
                "content": "resume from review",
            },
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertFalse(payload["dispatched"])
        self.assertEqual(created["run_id"], payload["run_id"])
        self.assertEqual("executing", payload["run"]["phase"])
        self.assertIn("resume_from_review", payload["messages"][2]["content"])
        self.assertIn("linked to run", payload["messages"][1]["content"])

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
        self.assertEqual(
            ["operator", "system", "agent"],
            [item["role"] for item in history_payload["items"]],
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

    def test_sync_execution_access_notices_rewrites_stored_message(self) -> None:
        thread = chat_store.create_thread(
            workspace_id="workspace_alpha",
            run_id=None,
            thread_kind="ide",
            created_at="2026-08-06T10:00:00Z",
        )
        chat_store.save_message(
            {
                "message_id": "message_agent_notice",
                "thread_id": thread["thread_id"],
                "workspace_id": "workspace_alpha",
                "run_id": "",
                "role": "agent",
                "content": (
                    "Agent mode is consultative-only. Enable Full Access in the "
                    "Agent Dock composer to let the agent edit files and run commands."
                ),
                "created_at": "2026-08-06T10:00:01Z",
            }
        )
        # An unrelated message must be left untouched.
        chat_store.save_message(
            {
                "message_id": "message_agent_unrelated",
                "thread_id": thread["thread_id"],
                "workspace_id": "workspace_alpha",
                "run_id": "",
                "role": "agent",
                "content": "Ran the test suite, all green.",
                "created_at": "2026-08-06T10:00:02Z",
            }
        )

        response = self.client.post(
            f"/api/chat/threads/{thread['thread_id']}/execution-access-notices",
            json={"execution_access": "full"},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.json()["updated"])

        history = self.client.get(f"/api/chat/threads/{thread['thread_id']}/history").json()
        contents = {item["message_id"]: item["content"] for item in history["items"]}
        self.assertEqual(
            "Agent mode now has Full Access enabled — the agent can edit files and run commands.",
            contents["message_agent_notice"],
        )
        self.assertEqual("Ran the test suite, all green.", contents["message_agent_unrelated"])

        # Flipping back to consultative rewrites it the other way.
        back = self.client.post(
            f"/api/chat/threads/{thread['thread_id']}/execution-access-notices",
            json={"execution_access": "consultative"},
        )
        self.assertEqual(1, back.json()["updated"])
        history_2 = self.client.get(f"/api/chat/threads/{thread['thread_id']}/history").json()
        contents_2 = {item["message_id"]: item["content"] for item in history_2["items"]}
        self.assertEqual(
            "Agent mode is consultative-only. Enable Full Access in the "
            "Agent Dock composer to let the agent edit files and run commands.",
            contents_2["message_agent_notice"],
        )

    def test_sync_execution_access_notices_missing_thread_returns_404(self) -> None:
        response = self.client.post(
            "/api/chat/threads/thread_missing/execution-access-notices",
            json={"execution_access": "full"},
        )
        self.assertEqual(404, response.status_code)

    def test_history_caps_long_running_thread_by_default(self) -> None:
        # 151 posts exceeds the mutating-API rate limit's default (120/min) window;
        # lift it for this test's bursty traffic and reset shared state after so it
        # can't leak into other tests.
        reset_rate_limit_state_for_tests()
        self.addCleanup(reset_rate_limit_state_for_tests)
        rate_limit_env = patch.dict(
            os.environ,
            {"AXON_WATCH_MUTATING_RATE_LIMIT_PER_MINUTE": "10000"},
            clear=False,
        )
        rate_limit_env.start()
        self.addCleanup(rate_limit_env.stop)

        created = self.client.post(
            "/api/chat/messages",
            json={"workspace_id": "workspace_alpha", "content": "seed"},
        ).json()
        thread_id = created["thread_id"]
        for index in range(150):
            self.client.post(
                "/api/chat/messages",
                json={
                    "workspace_id": "workspace_alpha",
                    "content": f"followup {index}",
                    "thread_id": thread_id,
                },
            )
        # Seed thread posts 3 messages/turn (operator+system+agent); 151 turns = 453.
        full_history = self.client.get(f"/api/chat/threads/{thread_id}/history").json()
        self.assertGreater(full_history["total_count"], 80)
        self.assertEqual(80, full_history["count"])
        self.assertEqual(80, len(full_history["items"]))
        # Capped response keeps the *tail* (most recent) messages: each posted
        # turn writes operator/system/agent, so the last turn's operator
        # message sits three slots from the end.
        self.assertEqual("operator", full_history["items"][-3]["role"])
        self.assertEqual("followup 149", full_history["items"][-3]["content"])

        uncapped = self.client.get(
            f"/api/chat/threads/{thread_id}/history", params={"limit": 0}
        ).json()
        self.assertEqual(full_history["total_count"], uncapped["count"])
        self.assertEqual(full_history["total_count"], uncapped["total_count"])

    def test_get_workspace_chat_thread_returns_latest_operator_thread(self) -> None:
        first = self.client.post(
            "/api/chat/messages",
            json={"workspace_id": "workspace_alpha", "content": "first command"},
        ).json()
        second = self.client.post(
            "/api/chat/messages",
            json={"workspace_id": "workspace_alpha", "content": "second command"},
        ).json()

        self.assertEqual(first["thread_id"], second["thread_id"])

        response = self.client.get("/api/workspaces/workspace_alpha/chat/thread?surface=operator")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(second["thread_id"], payload["thread_id"])
        self.assertEqual("workspace_alpha", payload["workspace_id"])
        self.assertEqual("operator", payload["thread_kind"])
        self.assertIn("updated_at", payload)

        history = self.client.get(f"/api/chat/threads/{payload['thread_id']}/history").json()
        self.assertEqual(6, history["count"])

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

    def test_workspace_chat_thread_separates_operator_and_ide_surfaces(self) -> None:
        operator = self.client.post(
            "/api/chat/messages",
            json={"workspace_id": "workspace_alpha", "content": "git status"},
        ).json()
        with patch(
            "app.chat.lane_b_post_message.generate_lane_b_result",
            return_value={
                "content": "Lane B reply",
                "dispatched": True,
                "runtime_id": "cursor_local",
                "runtime_label": "Cursor CLI (local)",
                "reason": "",
            },
        ):
            ide = self.client.post(
                "/api/chat/messages",
                json={
                    "workspace_id": "workspace_alpha",
                    "content": "Explain the repo layout.",
                    "composer_mode": "ask",
                },
            ).json()

        self.assertNotEqual(operator["thread_id"], ide["thread_id"])

        operator_thread = self.client.get(
            "/api/workspaces/workspace_alpha/chat/thread?surface=operator",
        ).json()
        ide_thread = self.client.get(
            "/api/workspaces/workspace_alpha/chat/thread?surface=ide",
        ).json()

        self.assertEqual(operator["thread_id"], operator_thread["thread_id"])
        self.assertEqual("operator", operator_thread["thread_kind"])
        self.assertEqual(ide["thread_id"], ide_thread["thread_id"])
        self.assertEqual("ide", ide_thread["thread_kind"])

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
