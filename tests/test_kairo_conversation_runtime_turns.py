from __future__ import annotations

from unittest.mock import patch

from tests.support.kairo_conversation_fixtures import (
    BRIEFING_PATCH,
    FLEET_PATCH,
    GRAPH_PATCH,
    KairoConversationTestCase,
    MOCK_BRIEFING,
    MOCK_FLEET,
    MOCK_GRAPH,
)

from app.kairo_conversation import converse_turn  # noqa: E402


class KairoConversationRuntimeTurnTests(KairoConversationTestCase):
    @patch(GRAPH_PATCH, return_value=MOCK_GRAPH)
    @patch(FLEET_PATCH, return_value=MOCK_FLEET)
    @patch(BRIEFING_PATCH, return_value=MOCK_BRIEFING)
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

    @patch(GRAPH_PATCH, return_value=MOCK_GRAPH)
    @patch(FLEET_PATCH, return_value=MOCK_FLEET)
    @patch(BRIEFING_PATCH, return_value=MOCK_BRIEFING)
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

    @patch(GRAPH_PATCH, return_value=MOCK_GRAPH)
    @patch(FLEET_PATCH, return_value=MOCK_FLEET)
    @patch(BRIEFING_PATCH, return_value=MOCK_BRIEFING)
    @patch("app.kairo_conversation.dispatch_ide_composer")
    @patch(
        "app.kairo_conversation_runtime_context.build_lane_b_context_block",
        return_value="Workspace context",
    )
    def test_school_capability_question_uses_consultative_runtime(
        self,
        _mock_context: object,
        mock_dispatch,
        *_mocks: object,
    ) -> None:
        mock_dispatch.return_value = {
            "content": "Imani can coordinate this, provided teachers approve grades and parent messages.",
            "dispatched": True,
        }
        payload = converse_turn(
            content=(
                "Will Imani in Young Eagles be able to help me run the school, post daily "
                "homework, help grade it, and prepare parent reports?"
            ),
            session_id="school-capability-session",
            workspace_id="workspace_young_eagles_day_care",
            use_runtime=True,
            answer_tier="deep",
            submission_intent="ask",
        )
        self.assertEqual("open_question", payload["turn_kind"])
        self.assertEqual("model", payload["source"])
        self.assertIn("Imani can coordinate", str(payload["reply"]))
        mock_dispatch.assert_called_once()

    @patch(GRAPH_PATCH, return_value=MOCK_GRAPH)
    @patch(FLEET_PATCH, return_value=MOCK_FLEET)
    @patch(BRIEFING_PATCH, return_value=MOCK_BRIEFING)
    @patch("app.kairo_conversation.dispatch_ide_composer")
    @patch(
        "app.kairo_conversation_runtime_context.build_lane_b_context_block",
        return_value="Workspace context",
    )
    def test_ask_always_uses_consultative_runtime_without_keyword_matching(
        self,
        _mock_context: object,
        mock_dispatch,
        *_mocks: object,
    ) -> None:
        mock_dispatch.return_value = {
            "content": "Here is my considered recommendation.",
            "dispatched": True,
        }
        payload = converse_turn(
            content="I have a new idea.",
            session_id="consultative-ask-session",
            use_runtime=False,
            answer_tier="fast",
            submission_intent="ask",
        )
        self.assertEqual("model", payload["source"])
        self.assertIn("considered recommendation", str(payload["reply"]))
        mock_dispatch.assert_called_once()

    @patch(GRAPH_PATCH, return_value=MOCK_GRAPH)
    @patch(FLEET_PATCH, return_value=MOCK_FLEET)
    @patch(BRIEFING_PATCH, return_value=MOCK_BRIEFING)
    @patch(
        "app.kairo_conversation.dispatch_ide_composer",
        return_value={"content": "", "dispatched": False},
    )
    def test_school_capability_question_has_useful_template_fallback(
        self,
        *_mocks: object,
    ) -> None:
        payload = converse_turn(
            content="Can Imani help me run the school and send weekly parent updates?",
            session_id="school-fallback-session",
            workspace_id="workspace_young_eagles_day_care",
            submission_intent="ask",
        )
        self.assertEqual("open_question", payload["turn_kind"])
        self.assertIn("Imani", str(payload["reply"]))
        self.assertIn("teacher sign-off", str(payload["reply"]))
        self.assertNotIn("run queue is idle", str(payload["reply"]).lower())

    @patch(GRAPH_PATCH, return_value=MOCK_GRAPH)
    @patch(FLEET_PATCH, return_value=MOCK_FLEET)
    @patch(BRIEFING_PATCH, return_value=MOCK_BRIEFING)
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

    @patch(GRAPH_PATCH, return_value=MOCK_GRAPH)
    @patch(FLEET_PATCH, return_value=MOCK_FLEET)
    @patch(BRIEFING_PATCH, return_value=MOCK_BRIEFING)
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
        self.assertEqual(
            artifact_body.count("If you are seeing a spike in Supabase or Axon quota"),
            1,
        )
        self.assertTrue(spoken.endswith((".", "!", "?")))

    @patch(GRAPH_PATCH, return_value=MOCK_GRAPH)
    @patch(FLEET_PATCH, return_value=MOCK_FLEET)
    @patch(BRIEFING_PATCH, return_value=MOCK_BRIEFING)
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
        self.assertRegex(
            str(payload["reply"]).lower(),
            r"(approval|approve|approvals|sign-?off)",
        )
        mock_dispatch.assert_not_called()
