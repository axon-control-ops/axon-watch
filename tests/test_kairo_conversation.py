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


from app.kairo.context_pack_cache import clear_pack_cache_for_tests  # noqa: E402
from app.kairo.turn_memory import clear_memory_for_tests  # noqa: E402


class KairoConversationUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_pack_cache_for_tests()
        clear_memory_for_tests()

    def test_classify_command_turn(self) -> None:
        self.assertEqual("command", classify_conversation_turn("git status"))
        self.assertEqual("command", classify_conversation_turn("what is the git status?"))
        self.assertEqual("command", classify_conversation_turn("run ./scripts/dev/check-health.sh"))

    def test_classify_status_question(self) -> None:
        self.assertEqual("status_question", classify_conversation_turn("any approvals?"))
        self.assertEqual("status_question", classify_conversation_turn("what needs my attention"))
        self.assertEqual(
            "status_question",
            classify_conversation_turn("check what DashPro workspace just did"),
        )
        self.assertEqual(
            "status_question",
            classify_conversation_turn("pull up DashPro workspace and check what is doing"),
        )

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

    def test_answer_general_surfaces_cli_blocker_instead_of_nominal(self) -> None:
        pack = {
            "briefing": {
                **_MOCK_BRIEFING,
                "pending_approvals": {"count": 0},
                "active_runs": [],
                "top_signals": [],
                "notice": "No active runs. Systems nominal.",
                "cli_runtime": {
                    "dispatch_ready": False,
                    "blockers": ["Cursor CLI (local): Cursor auth probe timed out."],
                },
            },
            "fleet": {"critical_count": 0, "attention_count": 0, "workspace_count": 1},
        }
        reply = answer_status_question("is everything normal?", pack)
        self.assertIn("agent dispatch is blocked", reply)
        self.assertIn("Cursor auth probe timed out", reply)
        self.assertNotIn("Systems look nominal", reply)

    def test_answer_health_question_is_concise_when_operational(self) -> None:
        pack = {
            "briefing": {
                **_MOCK_BRIEFING,
                "pending_approvals": {"count": 0},
                "active_runs": [],
                "top_signals": [],
                "notice": "No active runs. Systems nominal.",
                "cli_runtime": {"dispatch_ready": True, "blockers": []},
                "degraded": {"active": False, "reasons": []},
            },
            "fleet": {"critical_count": 0, "attention_count": 0, "workspace_count": 1},
        }
        reply = answer_status_question("is everything normal on your side?", pack)
        self.assertIn("all clear", reply.lower())
        self.assertLess(len(reply), 120)
        self.assertNotIn("Resume Before we keep pushing OTAs", reply)

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
        self.assertFalse(payload["requires_confirmation"])
        self.assertIn("git status", str(payload["reply"]).lower())
        self.assertEqual("template", payload["source"])
        self.assertEqual([], payload["artifacts"])

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    def test_converse_execute_tier_command_requires_confirmation(
        self,
        *_mocks: object,
    ) -> None:
        payload = converse_turn(
            content="run ./scripts/dev/check-health.sh",
            session_id="confirm-session",
        )
        self.assertEqual("command", payload["turn_kind"])
        self.assertTrue(payload["requires_confirmation"])
        self.assertIn("say yes", str(payload["reply"]).lower())

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    def test_followup_yes_dispatches_pending_command(
        self,
        *_mocks: object,
    ) -> None:
        converse_turn(
            content="run npm run verify",
            session_id="yes-session",
        )
        payload = converse_turn(content="yes", session_id="yes-session")
        self.assertEqual("action", payload["turn_kind"])
        action = payload["action"]
        assert isinstance(action, dict)
        self.assertEqual("dispatch_command", action.get("type"))
        self.assertEqual("run npm run verify", action.get("content"))

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    def test_followup_yes_opens_briefing_surface(
        self,
        *_mocks: object,
    ) -> None:
        import app.kairo_conversation as kc

        kc._remember_entities("briefing-surface-session", pending_briefing_surface="1")
        payload = converse_turn(content="yes", session_id="briefing-surface-session")
        self.assertEqual("action", payload["turn_kind"])
        action = payload["action"]
        assert isinstance(action, dict)
        self.assertEqual("focus_briefing", action.get("type"))
        self.assertIn("opening the briefing", str(payload["reply"]).lower())

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    def test_note_briefing_surface_offer_sets_pending_surface(
        self,
        *_mocks: object,
    ) -> None:
        import app.kairo_conversation as kc

        kc._remember_entities("briefing-offer-session", pending_briefing_surface="")
        kc._note_briefing_surface_offer(
            "briefing-offer-session",
            "Two runs are active. Shall I pull it to the front?",
        )
        entity = kc._entity_context("briefing-offer-session")
        self.assertEqual("1", entity.get("pending_briefing_surface"))

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    def test_converse_question_style_git_status_routes_as_command(
        self,
        *_mocks: object,
    ) -> None:
        payload = converse_turn(content="what is the git status?", session_id="test-session")
        self.assertEqual("command", payload["turn_kind"])
        self.assertEqual("git status", payload["command_content"])
        self.assertIn("git status", str(payload["reply"]).lower())

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
        self.assertEqual("workspace_dashpro", action.get("target_workspace_id"))

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
    def test_converse_mangled_dashpro_workspace_activity_prompt_routes_to_status(
        self,
        mock_briefing,
        *_mocks: object,
    ) -> None:
        payload = converse_turn(
            content="hey vaccine can you check what this pro works based use it",
            session_id="dashpro-voice-session",
        )
        self.assertEqual("status_question", payload["turn_kind"])
        self.assertEqual("template", payload["source"])
        self.assertIn("DashPro", str(payload["reply"]))
        mock_briefing.assert_called_with(workspace_id="workspace_dashpro")

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    def test_converse_probox_space_doing_prompt_routes_to_status(
        self,
        mock_briefing,
        *_mocks: object,
    ) -> None:
        payload = converse_turn(
            content="hey excent can you pull up those probox space and check what is doing",
            session_id="dashpro-voice-session-2",
        )
        self.assertEqual("status_question", payload["turn_kind"])
        self.assertIn("DashPro", str(payload["reply"]))
        mock_briefing.assert_called_with(workspace_id="workspace_dashpro")

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    @patch("app.kairo_conversation.dispatch_ide_composer")
    @patch(
        "app.kairo_conversation_runtime_context.build_lane_b_context_block",
        return_value="Workspace context",
    )
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
            answer_tier="deep",
        )
        reply = str(payload["reply"])
        self.assertNotIn(":::", reply)
        self.assertNotIn("scripts/ops", reply)
        self.assertTrue(payload["artifacts"])
        artifact_body = str(payload["artifacts"][0]["body"])
        self.assertIn("DashPro is not spiking", artifact_body)

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    @patch("app.kairo_conversation.dispatch_ide_composer")
    @patch(
        "app.kairo_conversation_runtime_context.build_lane_b_context_block",
        return_value="Workspace context",
    )
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
            answer_tier="deep",
        )
        self.assertEqual("open_question", payload["turn_kind"])
        self.assertEqual("model", payload["source"])
        self.assertIn("Sentry spike", str(payload["artifacts"][0]["body"]))
        self.assertTrue(payload["artifacts"])
        mock_dispatch.assert_called_once()

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    @patch("app.kairo_conversation.dispatch_ide_composer")
    def test_converse_open_question_fast_tier_skips_runtime(
        self,
        mock_dispatch,
        *_mocks: object,
    ) -> None:
        payload = converse_turn(
            content="why is sentry spiking?",
            session_id="fast-open-question",
            use_runtime=True,
            answer_tier="fast",
        )
        self.assertEqual("open_question", payload["turn_kind"])
        self.assertEqual("template", payload["source"])
        self.assertEqual([], payload["artifacts"])
        mock_dispatch.assert_not_called()

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    @patch("app.kairo_conversation.dispatch_ide_composer")
    @patch(
        "app.kairo_conversation_runtime_context.build_lane_b_context_block",
        return_value="Workspace context",
    )
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
            answer_tier="deep",
        )
        reply = str(payload["reply"])
        artifact_body = str(payload["artifacts"][0]["body"])
        self.assertLessEqual(len(reply), 280)
        self.assertIn("DashPro spike", artifact_body)
        self.assertEqual(artifact_body.count("If you are seeing a spike in Supabase or Axon quota"), 1)
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
        }
        self.assertEqual(expected, set(payload))
        self.assertEqual("status_question", payload["turn_kind"])
        self.assertTrue(payload["reply"])
