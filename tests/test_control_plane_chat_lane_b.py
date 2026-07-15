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

from app.main import app  # noqa: E402
from app.kairo.turn_memory import clear_memory_for_tests, remember_entities, remember_turn  # noqa: E402
from app.persistence import chat_store  # noqa: E402
from app.persistence import run_store  # noqa: E402


class ControlPlaneChatLaneBTests(unittest.TestCase):
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


    @patch(
        "app.chat.service.generate_lane_b_result",
        return_value={
            "content": "Runtime-backed reply",
            "dispatched": True,
            "runtime_id": "cursor_local",
            "runtime_label": "Cursor CLI (local)",
            "reason": "",
        },
    )
    def test_post_chat_message_lane_b_skips_command_dispatch(self, _mock_runtime) -> None:
        response = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_alpha",
                "content": "Explain how this workspace is wired.",
                "composer_mode": "ask",
            },
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertFalse(payload["dispatched"])
        self.assertIsNone(payload["run"])
        self.assertEqual(3, len(payload["messages"]))
        self.assertEqual("system", payload["messages"][1]["role"])
        self.assertIn("Lane B (ask)", payload["messages"][1]["content"])
        self.assertEqual("agent", payload["messages"][2]["role"])
        self.assertEqual("Runtime-backed reply", payload["messages"][2]["content"])

    @patch(
        "app.chat.service.generate_lane_b_result",
        return_value={
            "content": "Consultative agent reply",
            "dispatched": True,
            "runtime_id": "cursor_local",
            "runtime_label": "Cursor CLI (local)",
            "reason": "",
            "execution_tier": "consultative",
        },
    )
    def test_post_chat_message_lane_b_agent_full_access_executes_without_approval(
        self, _mock_runtime
    ) -> None:
        # Full Access consent replaces the per-run approval boundary.
        response = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_alpha",
                "content": "Implement the guarded slice.",
                "composer_mode": "agent",
                "execution_access": "full",
            },
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload["dispatched"])
        # Run executed in the same turn and auto-completed (no review queue).
        self.assertEqual("completed", payload["run"]["phase"])
        self.assertFalse(payload["run"]["can_approve"])
        self.assertNotIn("approval boundary", payload["messages"][1]["content"].lower())

    @patch(
        "app.chat.service.generate_lane_b_result",
        return_value={
            "content": "I inspected the workspace and propose the next bounded steps.",
            "dispatched": True,
            "runtime_id": "cursor_local",
            "runtime_label": "Cursor CLI (local)",
            "reason": "",
        },
    )
    def test_post_chat_message_lane_b_agent_creates_run_and_receipts(self, _mock_runtime) -> None:
        response = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_alpha",
                "content": "Implement the next thin slice.",
                "composer_mode": "agent",
            },
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload["dispatched"])
        self.assertIsNotNone(payload["run"])
        self.assertTrue(payload["run_id"].startswith("run_"))
        # Successful dispatch auto-completes the run.
        self.assertEqual("completed", payload["run"]["phase"])
        self.assertIn("runtime fabric", payload["messages"][1]["content"])
        self.assertIn("bounded steps", payload["messages"][2]["content"])

        history = self.client.get(f"/api/runs/{payload['run_id']}/history").json()
        receipt_types = [item["receipt"]["type"] for item in history["items"]]
        self.assertIn("runtime_dispatch", receipt_types)
        phases = [item["to_phase"] for item in history["items"]]
        self.assertIn("completed", phases)

    @patch("app.chat.service.generate_lane_b_result")
    def test_post_chat_message_lane_b_agent_greeting_stays_local(self, mock_runtime) -> None:
        response = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_alpha",
                "content": "Hey VAXON",
                "composer_mode": "agent",
                "execution_access": "full",
            },
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertFalse(payload["dispatched"])
        self.assertEqual("", payload["run_id"])
        self.assertIsNone(payload["run"])
        self.assertEqual("ide", self.client.get(
            f"/api/chat/threads/{payload['thread_id']}"
        ).json()["thread_kind"])
        self.assertIn("local reply", payload["messages"][1]["content"].lower())
        self.assertNotIn("lane b (agent)", payload["messages"][1]["content"].lower())
        self.assertTrue(payload["messages"][2]["content"])
        mock_runtime.assert_not_called()

    @patch(
        "app.chat.service.generate_lane_b_result",
        return_value={
            "content": "Fallback reply — runtime unavailable.",
            "dispatched": False,
            "runtime_id": "",
            "runtime_label": "",
            "reason": "runtime unavailable",
        },
    )
    def test_post_chat_message_lane_b_agent_failure_marks_run_failed(self, _mock_runtime) -> None:
        # Failed dispatches fail closed; the fallback error stays in the thread.
        response = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_alpha",
                "content": "Implement the next thin slice.",
                "composer_mode": "agent",
                "execution_access": "full",
            },
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertFalse(payload["dispatched"])
        self.assertEqual("failed", payload["run"]["phase"])

    def test_post_chat_message_lane_b_streaming_returns_placeholder_agent(self) -> None:
        def _streaming_lane_b_result(**kwargs):
            on_chunk = kwargs.get("on_chunk")
            if on_chunk is not None:
                on_chunk("Runtime-backed reply", "Runtime-backed reply")
            return {
                "content": "Runtime-backed reply",
                "dispatched": True,
                "runtime_id": "cursor_local",
                "runtime_label": "Cursor CLI (local)",
                "reason": "",
            }

        with patch.dict(os.environ, {"AXON_WATCH_LANE_B_STREAMING": "1"}, clear=False):
            with patch(
                "app.chat.service.generate_lane_b_result",
                side_effect=_streaming_lane_b_result,
            ):
                response = self.client.post(
                    "/api/chat/messages",
                    json={
                        "workspace_id": "workspace_alpha",
                        "content": "Stream this reply.",
                        "composer_mode": "ask",
                    },
                )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload["streaming"])
        self.assertTrue(payload["stream_agent_message_id"])
        self.assertEqual("", payload["messages"][2]["content"])
        self.assertIn("generating reply", payload["messages"][1]["content"].lower())

    def test_post_chat_message_lane_b_workspace_switch_returns_ui_action(self) -> None:
        response = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_axon_watch",
                "content": "Open and switch to the Dashpro workspace",
                "composer_mode": "agent",
                "execution_access": "full",
            },
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertFalse(payload["dispatched"])
        self.assertIsNone(payload["run"])
        ui_action = payload.get("ui_action")
        self.assertIsInstance(ui_action, dict)
        assert isinstance(ui_action, dict)
        self.assertEqual("switch_workspace", ui_action.get("type"))
        self.assertEqual("workspace_dashpro", ui_action.get("workspace_id"))
        self.assertIn("workspace_dashpro", payload["messages"][2]["content"])

    @patch(
        "app.chat.service.generate_lane_b_result",
        return_value={
            "content": "Picking up the DashPro investigation.",
            "dispatched": True,
            "runtime_id": "cursor_local",
            "runtime_label": "Cursor CLI (local)",
            "reason": "",
        },
    )
    def test_post_chat_message_agent_injects_kairo_memory_on_handoff_style_prompt(
        self,
        mock_runtime,
    ) -> None:
        remember_entities(
            "kairo:workspace_dashpro:thread_main",
            signal_title="DashPro payments degraded",
            target_workspace_id="workspace_dashpro",
            task='Investigate signal "DashPro payments degraded"',
        )
        remember_turn(
            "kairo:workspace_dashpro:thread_main",
            "user",
            "What is going on with DashPro payments?",
        )
        remember_turn(
            "kairo:workspace_dashpro:thread_main",
            "assistant",
            "DashPro payments are degraded after approval.",
        )
        response = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_dashpro",
                "content": 'Investigate signal "DashPro payments degraded"',
                "composer_mode": "agent",
                "execution_access": "full",
                "kairo_session_id": "kairo:workspace_dashpro:thread_main",
            },
        )
        self.assertEqual(200, response.status_code)
        context = mock_runtime.call_args.kwargs["context"]
        self.assertIn("KAIRO memory", context.memory_appendix or "")
        self.assertIn("DashPro payments degraded", context.memory_appendix or "")

    @patch(
        "app.chat.service.generate_lane_b_result",
        return_value={
            "content": "Continuing the teacher dashboard work.",
            "dispatched": True,
            "runtime_id": "cursor_local",
            "runtime_label": "Cursor CLI (local)",
            "reason": "",
            "execution_tier": "executing",
        },
    )
    def test_post_chat_message_agent_always_packs_ide_thread_history(
        self,
        mock_runtime,
    ) -> None:
        thread = chat_store.create_thread(
            workspace_id="workspace_alpha",
            run_id=None,
            thread_kind="ide",
            created_at="2026-07-13T10:00:00Z",
        )
        chat_store.save_message(
            {
                "message_id": "message_operator_prior",
                "thread_id": thread["thread_id"],
                "workspace_id": "workspace_alpha",
                "run_id": "",
                "role": "operator",
                "content": "Polish the teacher dashboard tests",
                "created_at": "2026-07-13T10:00:00Z",
            }
        )
        chat_store.save_message(
            {
                "message_id": "message_agent_prior",
                "thread_id": thread["thread_id"],
                "workspace_id": "workspace_alpha",
                "run_id": "",
                "role": "agent",
                "content": "Updating TeacherDashboardSecondaryMenu mocks",
                "created_at": "2026-07-13T10:00:01Z",
            }
        )
        response = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_alpha",
                "thread_id": thread["thread_id"],
                "content": "Yes please continue there",
                "composer_mode": "agent",
                "execution_access": "full",
                "kairo_session_id": "kairo:workspace_alpha:thread_main",
            },
        )
        self.assertEqual(200, response.status_code)
        context = mock_runtime.call_args.kwargs["context"]
        appendix = context.memory_appendix or ""
        self.assertIn("Recent IDE thread", appendix)
        self.assertIn("teacher dashboard", appendix)
        self.assertIn("TeacherDashboardSecondaryMenu", appendix)

    def test_thread_history_normalizes_agent_research_blocks_on_read(self) -> None:
        thread = chat_store.create_thread(
            workspace_id="workspace_alpha",
            run_id=None,
            created_at="2026-07-07T16:00:00Z",
            thread_kind="ide",
        )
        raw = (
            ":::research Web search\n"
            "- No web results | about:blank\n"
            """[{'text': {'text': '{"success": true, "query": "react hooks", """
            """"results": [], "provider": "duckduckgo_instant"}'}}]\n"""
            ":::\n"
        )
        chat_store.save_message(
            {
                "message_id": "message_agent_history_normalize",
                "thread_id": thread["thread_id"],
                "workspace_id": "workspace_alpha",
                "run_id": None,
                "role": "agent",
                "content": raw,
                "created_at": "2026-07-07T16:00:00Z",
            }
        )

        response = self.client.get(f"/api/chat/threads/{thread['thread_id']}/history")
        self.assertEqual(200, response.status_code)
        agent_messages = [item for item in response.json()["items"] if item["role"] == "agent"]
        self.assertEqual(1, len(agent_messages))
        normalized = agent_messages[0]["content"]
        self.assertNotIn("[{'text'", normalized)
        self.assertIn("react hooks", normalized)
