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
    build_conversation_context_pack,
    classify_conversation_turn,
    converse_turn,
)
from app.kairo_conversation_reply import compose_conversation_reply  # noqa: E402
from app.main import app  # noqa: E402
from app.persistence import chat_store, run_store  # noqa: E402

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

# Patches must target where the pack builder imports the symbols (not the facade).
_BRIEFING_PATCH = "app.kairo.conversation_context_pack.build_operator_briefing"
_FLEET_PATCH = "app.kairo.conversation_context_pack.build_operator_fleet_health"
_GRAPH_PATCH = "app.kairo.conversation_context_pack.build_operator_brain_graph"


class KairoConversationTurnTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_pack_cache_for_tests()
        clear_memory_for_tests()

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
    def test_followup_yes_dispatches_pending_command(
        self,
        *_mocks: object,
    ) -> None:
        # Command-looking text only seeds a pending confirmation under
        # explicit Dispatch intent — plain Ask must never set up dispatch-lane
        # state (see kairo_conversation.py's Ask safety boundary).
        converse_turn(
            content="run npm run verify",
            session_id="yes-session",
            submission_intent="dispatch",
        )
        # "yes" confirms a pending action — the client marks that as Dispatch.
        payload = converse_turn(
            content="yes", session_id="yes-session", submission_intent="dispatch"
        )
        self.assertEqual("action", payload["turn_kind"])
        action = payload["action"]
        assert isinstance(action, dict)
        self.assertEqual("dispatch_command", action.get("type"))
        self.assertEqual("run npm run verify", action.get("content"))

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
    def test_auto_dispatch_command_does_not_leave_stale_pending(
        self,
        *_mocks: object,
    ) -> None:
        from app.kairo.turn_memory import entity_context

        converse_turn(content="health", session_id="auto-pending-session")
        self.assertFalse(entity_context("auto-pending-session").get("pending_command"))
        payload = converse_turn(content="yes", session_id="auto-pending-session")
        action = payload.get("action")
        if isinstance(action, dict):
            self.assertNotEqual("dispatch_command", action.get("type"))

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
    def test_followup_yes_after_dig_in_offer_hands_off_to_ide(
        self,
        *_mocks: object,
    ) -> None:
        import app.kairo_conversation as kc

        kc._remember_entities(
            "dig-in-session",
            signal_id="signal_monitor_dashpro_sentry_recent_issues_warning",
            target_workspace_id="workspace_dashpro",
            task='Investigate signal "Sentry spike in DashPro": 3 unresolved issues',
            pending_dig_in="1",
        )
        # "yes" confirms a pending action — the client marks that as Dispatch.
        payload = converse_turn(
            content="yes", session_id="dig-in-session", submission_intent="dispatch"
        )
        self.assertEqual("action", payload["turn_kind"])
        action = payload["action"]
        assert isinstance(action, dict)
        self.assertEqual("handoff_signal", action.get("type"))
        self.assertEqual("workspace_dashpro", action.get("target_workspace_id"))
        self.assertIn("handing this off", str(payload["reply"]).lower())
        self.assertNotEqual("1", kc._entity_context("dig-in-session").get("pending_dig_in"))

    def test_note_dig_in_offer_sets_pending_dig_in(self) -> None:
        import app.kairo_conversation as kc
        from app.kairo.turn_memory import note_dig_in_offer

        kc._remember_entities("dig-in-offer-session", pending_dig_in="")
        note_dig_in_offer(
            "dig-in-offer-session",
            "DashPro Sentry is critical. Open Attention for DashPro Sentry critical?",
        )
        entity = kc._entity_context("dig-in-offer-session")
        self.assertEqual("1", entity.get("pending_dig_in"))
        self.assertNotEqual("1", entity.get("pending_briefing_surface"))

        kc._remember_entities("dig-in-offer-fallback", pending_dig_in="")
        note_dig_in_offer("dig-in-offer-fallback", "Something odd happened. Want me to open Attention?")
        self.assertEqual("1", kc._entity_context("dig-in-offer-fallback").get("pending_dig_in"))

        kc._remember_entities(
            "pull-logs-offer-session",
            pending_dig_in="",
            target_workspace_id="workspace_axon_watch",
            task='Investigate signal "Axon-X Fast Gate"',
        )
        note_dig_in_offer(
            "pull-logs-offer-session",
            "Fast Gate failed on drill-9. I can pull the failed logs.",
        )
        pull_entity = kc._entity_context("pull-logs-offer-session")
        self.assertEqual("1", pull_entity.get("pending_dig_in"))
        self.assertIn("log", str(pull_entity.get("task", "")).lower())

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
    def test_followup_pull_failed_logs_hands_off_to_ide(
        self,
        *_mocks: object,
    ) -> None:
        import app.kairo_conversation as kc

        kc._remember_entities(
            "pull-logs-session",
            signal_id="signal_ci_fast_gate",
            target_workspace_id="workspace_axon_watch",
            task='Investigate signal "Axon-X Fast Gate" — Pull failed CI logs',
            pending_dig_in="1",
        )
        payload = converse_turn(
            content="Pull the failed logs",
            session_id="pull-logs-session",
            submission_intent="dispatch",
        )
        self.assertEqual("action", payload["turn_kind"])
        action = payload["action"]
        assert isinstance(action, dict)
        self.assertEqual("handoff_signal", action.get("type"))
        self.assertEqual("workspace_axon_watch", action.get("target_workspace_id"))
        self.assertIn("log", str(action.get("task", "")).lower())

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
    def test_followup_yes_opens_briefing_surface(
        self,
        *_mocks: object,
    ) -> None:
        import app.kairo_conversation as kc

        kc._remember_entities("briefing-surface-session", pending_briefing_surface="1")
        # "yes" confirms a pending action — the client marks that as Dispatch.
        payload = converse_turn(
            content="yes",
            session_id="briefing-surface-session",
            submission_intent="dispatch",
        )
        self.assertEqual("action", payload["turn_kind"])
        action = payload["action"]
        assert isinstance(action, dict)
        self.assertEqual("focus_briefing", action.get("type"))
        self.assertIn("opening the briefing", str(payload["reply"]).lower())

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
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

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
    def test_converse_question_style_git_status_routes_as_command(
        self,
        *_mocks: object,
    ) -> None:
        # Command-looking text only reaches the bounded-command lane with
        # explicit Dispatch intent — plain Ask leaves it a status question.
        payload = converse_turn(
            content="what is the git status?",
            session_id="test-session",
            submission_intent="dispatch",
        )
        self.assertEqual("command", payload["turn_kind"])
        self.assertEqual("git status", payload["command_content"])
        self.assertIn("git status", str(payload["reply"]).lower())

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
    def test_followup_handoff_action(
        self,
        *_mocks: object,
    ) -> None:
        converse_turn(
            content="what needs my attention?",
            session_id="followup-session",
        )
        payload = converse_turn(
            content="hand it off", session_id="followup-session", submission_intent="dispatch"
        )
        self.assertEqual("action", payload["turn_kind"])
        action = payload["action"]
        assert isinstance(action, dict)
        self.assertEqual("handoff_signal", action.get("type"))
        self.assertEqual("workspace_dashpro", action.get("target_workspace_id"))

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
    def test_converse_status_question_is_fast_template(
        self,
        *_mocks: object,
    ) -> None:
        payload = converse_turn(content="any approvals?", session_id="test-session-2")
        self.assertEqual("status_question", payload["turn_kind"])
        self.assertEqual("template", payload["source"])
        self.assertIn("2", str(payload["reply"]))
        self.assertRegex(str(payload["reply"]).lower(), r"(approval|approve|approvals)")

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
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

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
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

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
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

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
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

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
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

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
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
        spoken = str(payload.get("spoken_reply") or reply)
        artifact_body = str(payload["artifacts"][0]["body"])
        # Deep/runtime turns keep the full reply for UI; TTS may shorten.
        self.assertLessEqual(len(spoken), 900)
        self.assertGreaterEqual(len(reply), len(spoken))
        self.assertIn("DashPro spike", artifact_body)
        self.assertIn("storage", reply.lower())
        self.assertEqual(artifact_body.count("If you are seeing a spike in Supabase or Axon quota"), 1)
        self.assertTrue(spoken.endswith((".", "!", "?")))

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
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
        self.assertRegex(str(payload["reply"]).lower(), r"(approval|approve|approvals|sign-?off)")
        mock_dispatch.assert_not_called()

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
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
        self.assertIn("2", first)
        self.assertIn("2", second)
        self.assertRegex(first.lower(), r"(approval|approve|approvals)")
        self.assertRegex(second.lower(), r"(approval|approve|approvals)")
        self.assertNotEqual(first, second)
