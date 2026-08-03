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

_PASTED_LEAD_ROLLUP = """Lead rollup (Dana) — plan lead-plan-4816b40edb8547c0 still active.

Done: Reviewed Soren run_b29ce3a2af86 / task-bbe0de3a1b0f4104 — status completed but
delivery was no_change (no billing restore, no Vercel push receipt).

Verified in flight: Soren on task-4e1616a270854678 / run_6116c9959326 (strict retry).
Still open on plan: integrations item task-66ebd55565f44183. Next: wait for receipts.
"""


from app.kairo.context_pack_cache import clear_pack_cache_for_tests  # noqa: E402
from app.kairo.turn_memory import clear_memory_for_tests  # noqa: E402


class KairoConversationUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_pack_cache_for_tests()
        clear_memory_for_tests()
        # MUST isolate before reset_store — otherwise this deletes the operator's live chat DB.
        isolate_control_plane_db(self, run_store)
        chat_store.reset_store()

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

    def test_pasted_lead_rollup_is_ask_evidence_not_a_command(self) -> None:
        self.assertEqual("status_question", classify_conversation_turn(_PASTED_LEAD_ROLLUP))

    @patch("app.kairo_conversation._resolve_followup_action")
    @patch("app.kairo_conversation.maybe_handle_early_converse_intent")
    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    def test_pasted_lead_rollup_skips_all_action_shortcuts(
        self,
        _briefing: object,
        _fleet: object,
        _graph: object,
        early_intent: object,
        followup: object,
    ) -> None:
        payload = converse_turn(content=_PASTED_LEAD_ROLLUP, session_id="pasted-rollup")
        self.assertEqual("status_question", payload["turn_kind"])
        early_intent.assert_not_called()
        followup.assert_not_called()

    def test_classify_open_question_not_status(self) -> None:
        self.assertEqual("open_question", classify_conversation_turn("why is sentry spiking?"))
        self.assertEqual("open_question", classify_conversation_turn("how did this happen?"))

    def test_classify_chat_greeting(self) -> None:
        self.assertEqual("chat", classify_conversation_turn("hello there"))
        self.assertEqual("chat", classify_conversation_turn("thanks"))

    def test_answer_approvals_from_dto(self) -> None:
        pack = {"briefing": _MOCK_BRIEFING, "fleet": {"critical_count": 0}}
        reply = answer_status_question("any approvals waiting?", pack)
        self.assertIn("2 jobs", reply)
        self.assertTrue(
            "Approvals" in reply or "yes or no" in reply.lower() or "sign-off" in reply.lower()
        )

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
    def test_context_pack_includes_recent_workspace_dialogue(self, *_mocks: object) -> None:
        thread = chat_store.create_thread(
            workspace_id="workspace_dashpro",
            run_id=None,
            created_at="2026-07-13T08:00:00Z",
            thread_kind="operator",
        )
        chat_store.save_message(
            {
                "message_id": "message_operator_context_pack",
                "thread_id": thread["thread_id"],
                "workspace_id": "workspace_dashpro",
                "run_id": None,
                "role": "operator",
                "content": "DashPro payments are still failing after approval.",
                "created_at": "2026-07-13T08:00:01Z",
            }
        )
        chat_store.save_message(
            {
                "message_id": "message_agent_context_pack",
                "thread_id": thread["thread_id"],
                "workspace_id": "workspace_dashpro",
                "run_id": None,
                "role": "agent",
                "content": "I traced it to the retry path.",
                "created_at": "2026-07-13T08:00:02Z",
            }
        )
        pack = build_conversation_context_pack(workspace_id="workspace_dashpro")
        self.assertEqual(2, len(pack["recent_dialogue"]))
        self.assertEqual("operator", pack["recent_dialogue"][0]["role"])
        self.assertIn("payments are still failing", pack["recent_dialogue"][0]["content"])

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value={"items": []})
    @patch(
        "app.kairo_conversation.build_operator_briefing",
        return_value={
            **_MOCK_BRIEFING,
            "pending_approvals": {"count": 0, "items": []},
            "active_runs": [],
            "top_signals": [],
            "notice": "",
            "advise": "",
        },
    )
    def test_followup_template_reply_can_reference_recent_workspace_dialogue(self, *_mocks: object) -> None:
        thread = chat_store.create_thread(
            workspace_id="workspace_dashpro",
            run_id=None,
            created_at="2026-07-13T08:05:00Z",
            thread_kind="operator",
        )
        chat_store.save_message(
            {
                "message_id": "message_operator_followup",
                "thread_id": thread["thread_id"],
                "workspace_id": "workspace_dashpro",
                "run_id": None,
                "role": "operator",
                "content": "DashPro payments are still failing after approval.",
                "created_at": "2026-07-13T08:05:01Z",
            }
        )
        pack = build_conversation_context_pack(workspace_id="workspace_dashpro")
        reply = compose_conversation_reply(
            content="what about that?",
            pack=pack,
            session_id="followup-dialogue-pack",
            recent_turns=[],
        )
        self.assertIn("DashPro", reply)
        self.assertIn("payments", reply.lower())

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
