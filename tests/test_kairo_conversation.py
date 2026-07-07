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
