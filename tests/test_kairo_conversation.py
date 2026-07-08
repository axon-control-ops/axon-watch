from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo_conversation import (  # noqa: E402
    answer_status_question,
    classify_conversation_turn,
    converse_turn,
)
from app.kairo_conversation_reply import compose_conversation_reply  # noqa: E402
from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402

_MOCK_BRIEFING = {
    "generated_at": "2026-07-08T00:00:00Z",
    "notice": "Two runs are active.",
    "advise": "Review the top signal before dispatching more work.",
    "top_signals": [
        {
            "signal_id": "signal_monitor_dashpro_sentry_recent_issues_warning",
            "workspace_id": "workspace_dashpro",
            "title": "Sentry spike in DashPro",
            "summary": "3 unresolved issues",
            "severity": "high",
        }
    ],
    "pending_approvals": {"count": 2, "items": [{}, {}]},
    "active_runs": [{"run_id": "run_1", "summary": "Git status"}],
    "degraded": {"active": False, "reasons": []},
}

_MOCK_FLEET = {
    "items": [
        {"workspace_id": "ws_a", "tone": "critical"},
        {"workspace_id": "ws_b", "tone": "nominal"},
    ]
}

_MOCK_GRAPH = {"nodes": [{"node_id": "n1"}], "edges": []}


class KairoConversationUnitTests(unittest.TestCase):
    def test_classify_command_turn(self) -> None:
        self.assertEqual("command", classify_conversation_turn("git status"))
        self.assertEqual("command", classify_conversation_turn("run ./scripts/dev/check-health.sh"))

    def test_classify_status_question(self) -> None:
        self.assertEqual("status_question", classify_conversation_turn("any approvals?"))
        self.assertEqual("status_question", classify_conversation_turn("what needs my attention"))

    def test_classify_open_question_not_status(self) -> None:
        self.assertEqual("open_question", classify_conversation_turn("why is sentry spiking?"))
        self.assertEqual("open_question", classify_conversation_turn("how did this happen?"))

    def test_classify_chat_greeting(self) -> None:
        self.assertEqual("chat", classify_conversation_turn("hello there"))
        self.assertEqual("chat", classify_conversation_turn("thanks"))

    def test_answer_approvals_from_dto(self) -> None:
        pack = {"briefing": _MOCK_BRIEFING, "fleet": {"critical_count": 0}}
        reply = answer_status_question("any approvals waiting?", pack)
        self.assertIn("2 approval", reply)

    def test_answer_attention_uses_top_signal(self) -> None:
        pack = {
            "briefing": {**_MOCK_BRIEFING, "pending_approvals": {"count": 0}},
            "fleet": {"critical_count": 0, "attention_count": 1, "workspace_count": 2},
        }
        reply = answer_status_question("what's on fire?", pack)
        self.assertIn("Sentry spike", reply)

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    def test_converse_command_returns_ack_and_content(
        self,
        *_mocks: object,
    ) -> None:
        payload = converse_turn(content="git status", session_id="test-session")
        self.assertEqual("command", payload["turn_kind"])
        self.assertEqual("git status", payload["command_content"])
        self.assertIn("git status", str(payload["reply"]).lower())
        self.assertEqual("template", payload["source"])

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    def test_followup_handoff_action(
        self,
        *_mocks: object,
    ) -> None:
        converse_turn(
            content="what needs my attention?",
            session_id="followup-session",
        )
        payload = converse_turn(content="hand it off", session_id="followup-session")
        self.assertEqual("action", payload["turn_kind"])
        action = payload["action"]
        assert isinstance(action, dict)
        self.assertEqual("handoff_signal", action.get("type"))

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    def test_converse_status_question_is_fast_template(
        self,
        *_mocks: object,
    ) -> None:
        payload = converse_turn(content="any approvals?", session_id="test-session-2")
        self.assertEqual("status_question", payload["turn_kind"])
        self.assertEqual("template", payload["source"])
        self.assertIn("2 approval", str(payload["reply"]))

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    @patch("app.kairo_conversation.dispatch_ide_composer")
    @patch("app.kairo_conversation.build_lane_b_context_block", return_value="Workspace context")
    def test_converse_open_question_sanitizes_runtime_agent_dump(
        self,
        _mock_context: object,
        mock_dispatch,
        *_mocks: object,
    ) -> None:
        mock_dispatch.return_value = {
            "content": (
                ":::thinking\nInvestigating.\n:::\n"
                ":::tool Read scripts/ops/audit-supabase-storage.mjs\n\n"
                "From my side right now, DashPro is not spiking — systems nominal."
            ),
            "dispatched": True,
        }
        payload = converse_turn(
            content="why is dashpro spiking?",
            session_id="sanitize-open-question",
            use_runtime=True,
        )
        reply = str(payload["reply"])
        self.assertNotIn(":::", reply)
        self.assertNotIn("scripts/ops", reply)
        self.assertIn("DashPro is not spiking", reply)

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    @patch("app.kairo_conversation.dispatch_ide_composer")
    @patch("app.kairo_conversation.build_lane_b_context_block", return_value="Workspace context")
    def test_converse_open_question_uses_runtime_assistant(
        self,
        _mock_context: object,
        mock_dispatch,
        *_mocks: object,
    ) -> None:
        mock_dispatch.return_value = {
            "content": "The Sentry spike appears tied to the latest DashPro changes.",
            "dispatched": True,
        }
        payload = converse_turn(
            content="why is sentry spiking?",
            session_id="open-question-session",
            use_runtime=True,
        )
        self.assertEqual("open_question", payload["turn_kind"])
        self.assertEqual("model", payload["source"])
        self.assertIn("Sentry spike", str(payload["reply"]))
        mock_dispatch.assert_called_once()

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    @patch("app.kairo_conversation.dispatch_ide_composer")
    @patch("app.kairo_conversation.build_lane_b_context_block", return_value="Workspace context")
    def test_converse_open_question_trims_run_on_runtime_tail(
        self,
        _mock_context: object,
        mock_dispatch,
        *_mocks: object,
    ) -> None:
        mock_dispatch.return_value = {
            "content": (
                "I'll check operational docs and recent monitoring signals in the workspace to see what "
                "might explain a DashPro spike. If you are seeing a spike in Supabase or Axon quota, "
                "the repo points at storage, not the database. Recent ops work was added because "
                "storage is blowing the one-gigabyte free tier; cleanup notes call out the tts-audio "
                "bucket at roughly four hundred twenty-seven megabytes as the main offender. "
                "If you meant CPU, errors, or traffic instead, say which dashboard and I will narrow "
                "it.From my side right now DashPro is not spiking — no active runs, no top signal, "
                "systems nominal. If you are seeing a spike in Supabase or Axon quota, the repo "
                "points at storage, not the database."
            ),
            "dispatched": True,
        }
        payload = converse_turn(
            content="why is dashpro spiking?",
            session_id="open-question-tail-trim",
            use_runtime=True,
        )
        reply = str(payload["reply"])
        self.assertLessEqual(len(reply), 1200)
        self.assertIn("DashPro spike", reply)
        self.assertEqual(reply.count("If you are seeing a spike in Supabase or Axon quota"), 1)
        self.assertTrue(reply.endswith((".", "!", "?")))

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    @patch("app.kairo_conversation.dispatch_ide_composer")
    def test_converse_status_question_stays_template_even_with_runtime_enabled(
        self,
        mock_dispatch,
        *_mocks: object,
    ) -> None:
        payload = converse_turn(
            content="any approvals?",
            session_id="runtime-status-session",
            use_runtime=True,
        )
        self.assertEqual("status_question", payload["turn_kind"])
        self.assertEqual("template", payload["source"])
        self.assertRegex(str(payload["reply"]).lower(), r"(approval|sign-?off)")
        mock_dispatch.assert_not_called()

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    def test_status_replies_vary_across_turns(
        self,
        *_mocks: object,
    ) -> None:
        pack = {
            "briefing": _MOCK_BRIEFING,
            "fleet": {"critical_count": 1, "attention_count": 0, "workspace_count": 2},
        }
        first = compose_conversation_reply(
            content="any approvals?",
            pack=pack,
            session_id="variety-session",
            recent_turns=[],
        )
        second = compose_conversation_reply(
            content="any approvals?",
            pack=pack,
            session_id="variety-session",
            recent_turns=[
                {"role": "user", "content": "any approvals?"},
                {"role": "assistant", "content": first},
            ],
        )
        self.assertIn("2 approval", first)
        self.assertIn("2 approval", second)
        self.assertNotEqual(first, second)


class KairoConversationEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    def test_converse_endpoint_shape(self, *_mocks: object) -> None:
        response = self.client.post(
            "/api/kairo/converse",
            json={"content": "any approvals?", "session_id": "endpoint-test"},
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(
            {"turn_kind", "reply", "source", "command_content", "action"},
            set(payload),
        )
        self.assertEqual("status_question", payload["turn_kind"])
        self.assertTrue(payload["reply"])
