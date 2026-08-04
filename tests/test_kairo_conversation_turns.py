from __future__ import annotations

from unittest.mock import patch

from tests.support.kairo_conversation_fixtures import (
    BRIEFING_PATCH as _BRIEFING_PATCH,
    FLEET_PATCH as _FLEET_PATCH,
    GRAPH_PATCH as _GRAPH_PATCH,
    KairoConversationTestCase,
    MOCK_BRIEFING as _MOCK_BRIEFING,
    MOCK_FLEET as _MOCK_FLEET,
    MOCK_GRAPH as _MOCK_GRAPH,
)

from app.kairo_conversation import (  # noqa: E402
    answer_status_question,
    build_conversation_context_pack,
    classify_conversation_turn,
    converse_turn,
)
from app.kairo_conversation_reply import compose_conversation_reply  # noqa: E402


class KairoConversationTurnTests(KairoConversationTestCase):
    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
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
        payload = converse_turn(content="yes", session_id="dig-in-session")
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
        payload = converse_turn(content="Pull the failed logs", session_id="pull-logs-session")
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
        payload = converse_turn(content="yes", session_id="briefing-surface-session")
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
        payload = converse_turn(content="what is the git status?", session_id="test-session")
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
        payload = converse_turn(content="hand it off", session_id="followup-session")
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
