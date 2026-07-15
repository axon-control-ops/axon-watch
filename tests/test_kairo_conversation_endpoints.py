from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

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

from app.kairo.context_pack_cache import clear_pack_cache_for_tests  # noqa: E402
from app.kairo.turn_memory import clear_memory_for_tests  # noqa: E402


class KairoConversationEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_pack_cache_for_tests()
        clear_memory_for_tests()
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
        expected = {
            "turn_kind", "reply", "source", "command_content",
            "requires_confirmation", "action", "artifacts", "active_participant",
            "action_tier", "dispatch_lane", "voice_routing_mode",
            "model_receipt", "routing_receipt",
        }
        self.assertEqual(expected, set(payload))
        self.assertEqual("status_question", payload["turn_kind"])
        self.assertTrue(payload["reply"])

    @patch("app.routes.operator.converse_turn", return_value={"turn_kind": "chat", "reply": "ok"})
    def test_converse_endpoint_passes_refresh_query_flag(self, mock_converse) -> None:
        response = self.client.post(
            "/api/kairo/converse?refresh=true",
            json={"content": "what changed?", "session_id": "refresh-query"},
        )
        self.assertEqual(200, response.status_code)
        self.assertTrue(mock_converse.called)
        self.assertTrue(mock_converse.call_args.kwargs["force_refresh"])
