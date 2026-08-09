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

from app.chat.thread_service import create_workspace_chat_thread  # noqa: E402
from app.cli_runtime.router import _build_prompt  # noqa: E402
from app.main import app  # noqa: E402
from app.persistence import chat_store, run_store  # noqa: E402
from app.workspace_agents.employee_persona_prompt import EMPLOYEE_PERSONA_MARKER  # noqa: E402


class EmployeeChatThreadTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        chat_store.reset_store()
        self.addCleanup(chat_store.reset_store)

    def test_create_finds_existing_employee_thread(self) -> None:
        first = create_workspace_chat_thread(
            "workspace_axon_watch",
            thread_kind="ide",
            title="Quinn · Integrations",
            employee_id="employee-workspace_axon_watch-integrations-4",
            employee_role="integrations",
        )
        second = create_workspace_chat_thread(
            "workspace_axon_watch",
            thread_kind="ide",
            title="Quinn · Integrations",
            employee_id="employee-workspace_axon_watch-integrations-4",
            employee_role="integrations",
        )
        self.assertEqual(first["thread_id"], second["thread_id"])
        self.assertEqual("Quinn · Integrations", second["preview_label"])
        found = chat_store.find_thread_for_employee(
            "workspace_axon_watch",
            employee_id="employee-workspace_axon_watch-integrations-4",
            thread_kind="ide",
        )
        assert found is not None
        self.assertEqual(first["thread_id"], found["thread_id"])

    def test_list_preview_prefers_title(self) -> None:
        from app.chat.thread_service import list_workspace_chat_threads

        create_workspace_chat_thread(
            "workspace_axon_watch",
            thread_kind="ide",
            title="Jules · Frontend",
            employee_id="employee-workspace_axon_watch-frontend-2",
            employee_role="frontend",
        )
        listed = list_workspace_chat_threads("workspace_axon_watch", thread_kind="ide")
        labels = [str(item.get("preview_label")) for item in listed["items"]]
        self.assertIn("Jules · Frontend", labels)


class EmployeeChatThreadRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        chat_store.reset_store()
        self.addCleanup(chat_store.reset_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_http_create_dedupes_employee_thread(self) -> None:
        employee_id = "employee-workspace_axon_watch-backend-3"
        payload = {
            "surface": "ide",
            "title": "Reed · Backend",
            "employee_id": employee_id,
            "employee_role": "backend",
        }
        first = self.client.post(
            "/api/workspaces/workspace_axon_watch/chat/threads",
            json=payload,
        )
        second = self.client.post(
            "/api/workspaces/workspace_axon_watch/chat/threads",
            json=payload,
        )
        self.assertEqual(200, first.status_code)
        self.assertEqual(200, second.status_code)
        first_body = first.json()
        second_body = second.json()
        self.assertEqual(first_body["thread_id"], second_body["thread_id"])
        self.assertEqual(employee_id, first_body["employee_id"])
        self.assertEqual("backend", first_body["employee_role"])
        self.assertEqual("Reed · Backend", second_body["preview_label"])

    def test_http_list_includes_employee_thread_fields(self) -> None:
        created = self.client.post(
            "/api/workspaces/workspace_axon_watch/chat/threads",
            json={
                "surface": "ide",
                "title": "Quinn · Integrations",
                "employee_id": "employee-workspace_axon_watch-integrations-4",
                "employee_role": "integrations",
            },
        )
        self.assertEqual(200, created.status_code)
        thread_id = created.json()["thread_id"]

        listed = self.client.get(
            "/api/workspaces/workspace_axon_watch/chat/threads?surface=ide",
        )
        self.assertEqual(200, listed.status_code)
        match = next(
            item for item in listed.json()["items"] if item["thread_id"] == thread_id
        )
        self.assertEqual(
            "employee-workspace_axon_watch-integrations-4",
            match["employee_id"],
        )
        self.assertEqual("integrations", match["employee_role"])
        self.assertEqual("Quinn · Integrations", match["preview_label"])

    def test_history_normalizes_legacy_worker_start_card(self) -> None:
        thread = create_workspace_chat_thread(
            "workspace_dashpro",
            thread_kind="ide",
            title="Priya · Frontend",
            employee_id="employee-workspace_dashpro-frontend-2",
            employee_role="frontend",
        )
        chat_store.save_message(
            {
                "message_id": "message_operator_legacy_start",
                "thread_id": thread["thread_id"],
                "workspace_id": "workspace_dashpro",
                "run_id": "run_legacy",
                "role": "operator",
                "content": (
                    "Continuous worker dispatch started.\n"
                    "Role: frontend\n"
                    "Task: task-abc123def456\n"
                    "Run: run_legacy\n"
                    "Goal: Add previous-day navigation controls to Practice at Home."
                ),
                "created_at": "2026-08-09T12:00:00Z",
            }
        )

        body = self.client.get(f"/api/chat/threads/{thread['thread_id']}/history").json()
        item = body["items"][0]
        self.assertEqual("agent", item["role"])
        self.assertEqual("Priya", item["speaker_name"])
        self.assertEqual("frontend", item["speaker_role"])
        self.assertIn("Priya started this Frontend assignment.", item["content"])
        self.assertNotIn("Role: frontend", item["content"])

    def test_history_normalizes_legacy_queued_card_as_lead_authored(self) -> None:
        thread = create_workspace_chat_thread(
            "workspace_dashpro",
            thread_kind="ide",
            title="Priya · Frontend",
            employee_id="employee-workspace_dashpro-frontend-2",
            employee_role="frontend",
        )
        chat_store.save_message(
            {
                "message_id": "message_agent_legacy_queue",
                "thread_id": thread["thread_id"],
                "workspace_id": "workspace_dashpro",
                "run_id": "run_legacy_queue",
                "role": "agent",
                "content": "Queued for dispatch · Add previous-day navigation controls to Practice at Home.",
                "created_at": "2026-08-09T12:01:00Z",
            }
        )

        body = self.client.get(f"/api/chat/threads/{thread['thread_id']}/history").json()
        item = body["items"][0]
        self.assertEqual("agent", item["role"])
        self.assertEqual("Dana", item["speaker_name"])
        self.assertEqual("lead", item["speaker_role"])
        self.assertIn("Dana queued a Frontend assignment for Priya.", item["content"])
        self.assertNotIn("Queued for dispatch ·", item["content"])

    def test_http_employee_thread_skips_vaxon_persona_fast_path(self) -> None:
        streaming = patch.dict(os.environ, {"AXON_WATCH_LANE_B_STREAMING": "0"}, clear=False)
        streaming.start()
        self.addCleanup(streaming.stop)

        created = self.client.post(
            "/api/workspaces/workspace_axon_watch/chat/threads",
            json={
                "surface": "ide",
                "title": "Reed · Backend",
                "employee_id": "employee-workspace_axon_watch-backend-3",
                "employee_role": "backend",
            },
        )
        self.assertEqual(200, created.status_code)
        thread_id = created.json()["thread_id"]

        with patch(
            "app.chat.lane_b_post_message.generate_lane_b_result",
            return_value={
                "content": "Reed: continuing the backend shift.",
                "dispatched": True,
                "runtime_id": "cursor_local",
                "runtime_label": "Cursor CLI (local)",
                "reason": "",
                "execution_tier": "executing",
            },
        ) as mock_runtime:
            response = self.client.post(
                "/api/chat/messages",
                json={
                    "workspace_id": "workspace_axon_watch",
                    "thread_id": thread_id,
                    "content": "Hey VAXON",
                    "composer_mode": "agent",
                    "execution_access": "full",
                },
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        mock_runtime.assert_called_once()
        system_content = str(payload["messages"][1]["content"]).lower()
        self.assertNotIn("local reply", system_content)
        self.assertIn("lane b", system_content)
        self.assertEqual("Reed: continuing the backend shift.", payload["messages"][2]["content"])

    def test_http_employee_thread_skips_vaxon_persona_fast_path_when_streaming(self) -> None:
        streaming = patch.dict(os.environ, {"AXON_WATCH_LANE_B_STREAMING": "1"}, clear=False)
        streaming.start()
        self.addCleanup(streaming.stop)

        created = self.client.post(
            "/api/workspaces/workspace_axon_watch/chat/threads",
            json={
                "surface": "ide",
                "title": "Reed · Backend",
                "employee_id": "employee-workspace_axon_watch-backend-3",
                "employee_role": "backend",
            },
        )
        self.assertEqual(200, created.status_code)
        thread_id = created.json()["thread_id"]

        response = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_axon_watch",
                "thread_id": thread_id,
                "content": "Hey VAXON",
                "composer_mode": "agent",
                "execution_access": "full",
            },
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload["streaming"])
        self.assertTrue(payload["stream_agent_message_id"])
        system_content = str(payload["messages"][1]["content"]).lower()
        self.assertNotIn("local reply", system_content)
        self.assertIn("lane b", system_content)
        self.assertEqual("", payload["messages"][2]["content"])

    def test_http_agent_message_on_employee_thread_builds_persona_cli_prompt(self) -> None:
        streaming = patch.dict(os.environ, {"AXON_WATCH_LANE_B_STREAMING": "0"}, clear=False)
        streaming.start()
        self.addCleanup(streaming.stop)

        created = self.client.post(
            "/api/workspaces/workspace_axon_watch/chat/threads",
            json={
                "surface": "ide",
                "title": "Quinn · Integrations",
                "employee_id": "employee-workspace_axon_watch-integrations-4",
                "employee_role": "integrations",
            },
        )
        self.assertEqual(200, created.status_code)
        thread_id = created.json()["thread_id"]

        captured: dict[str, str] = {}

        def fake_dispatch(**kwargs):  # type: ignore[no-untyped-def]
            prompt = _build_prompt(
                composer_mode=str(kwargs.get("composer_mode") or "agent"),
                user_prompt=str(kwargs.get("user_prompt") or ""),
                context_block=str(kwargs.get("context_block") or ""),
                execution_tier="executing",
            )
            captured["prompt"] = prompt
            captured["context_block"] = str(kwargs.get("context_block") or "")
            return {
                "content": "Quinn: shift retried with receipts.",
                "dispatched": True,
                "runtime_id": "cursor_local",
                "runtime_label": "Cursor CLI (local)",
                "reason": "",
                "execution_tier": "executing",
            }

        with patch("app.chat.lane_b_agent.dispatch_ide_composer", side_effect=fake_dispatch):
            response = self.client.post(
                "/api/chat/messages",
                json={
                    "workspace_id": "workspace_axon_watch",
                    "thread_id": thread_id,
                    "content": "Retry the last failed shift and summarize receipts.",
                    "composer_mode": "agent",
                    "execution_access": "full",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertIn("prompt", captured)
        prompt = captured["prompt"]
        self.assertIn(EMPLOYEE_PERSONA_MARKER, prompt)
        self.assertIn("You are Quinn", prompt)
        self.assertIn("named employee in the Employee persona block", prompt)
        self.assertNotIn("You are Axon-X Lane B in Agent mode with Full Access.", prompt)
        self.assertLess(prompt.index(EMPLOYEE_PERSONA_MARKER), prompt.index("Workspace context:"))
        self.assertIn("You are Quinn", captured["context_block"])


if __name__ == "__main__":
    unittest.main()
