"""OP-C5 turn memory, pack TTL, and DashPro-scoped handoff contracts."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo.context_pack_cache import (  # noqa: E402
    clear_pack_cache_for_tests,
    get_cached_context_pack,
)
from app.kairo.turn_memory import (  # noqa: E402
    build_lane_b_memory_appendix,
    clear_memory_cache_for_tests,
    clear_memory_for_tests,
    entity_context,
    recent_turns,
    remember_entities,
    remember_turn,
    resolve_followup_action,
    session_key as turn_session_key,
)
from app.kairo_conversation import converse_turn  # noqa: E402
from app.kairo_voice import _HISTORY, _session_key as speak_session_key, generate_spoken_line  # noqa: E402
from app.persistence import run_store  # noqa: E402
from app.persistence.kairo_session_memory_store import _trim_to_byte_cap  # noqa: E402

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


class KairoTurnMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        clear_pack_cache_for_tests()
        clear_memory_for_tests()

    def test_turn_memory_cap_drops_oldest(self) -> None:
        session = "cap-session"
        for index in range(9):
            remember_turn(session, "user", f"turn-{index}")
        turns = recent_turns(session)
        self.assertEqual(8, len(turns))
        self.assertEqual("turn-1", turns[0]["content"])
        self.assertEqual("turn-8", turns[-1]["content"])

    def test_not_now_clears_pending_dig_in(self) -> None:
        session = "decline-dig-in-session"
        remember_entities(
            session,
            pending_dig_in="1",
            signal_id="signal_ci_1",
            target_workspace_id="workspace_dashpro",
            task="Investigate CI",
        )
        self.assertIsNone(resolve_followup_action("not now", session))
        self.assertNotIn("pending_dig_in", entity_context(session))

    def test_context_pack_ttl_reuses_within_window(self) -> None:
        builds: list[int] = []
        clock = {"t": 100.0}

        def builder() -> dict[str, object]:
            builds.append(1)
            return {"n": len(builds)}

        first = get_cached_context_pack(
            "workspace_dashpro",
            builder,
            now=lambda: clock["t"],
        )
        clock["t"] = 105.0
        second = get_cached_context_pack(
            "workspace_dashpro",
            builder,
            now=lambda: clock["t"],
        )
        self.assertIs(first, second)
        self.assertEqual(1, len(builds))
        clock["t"] = 111.0
        third = get_cached_context_pack(
            "workspace_dashpro",
            builder,
            now=lambda: clock["t"],
        )
        self.assertIsNot(first, third)
        self.assertEqual(2, len(builds))

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    def test_dashpro_scoped_status_then_handoff(
        self,
        mock_briefing: object,
        *_mocks: object,
    ) -> None:
        converse_turn(
            content="what's wrong with DashPro?",
            session_id="dashpro-handoff-session",
        )
        mock_briefing.assert_called_with(workspace_id="workspace_dashpro")
        payload = converse_turn(
            content="hand it off",
            session_id="dashpro-handoff-session",
        )
        self.assertEqual("action", payload["turn_kind"])
        action = payload["action"]
        assert isinstance(action, dict)
        self.assertEqual("handoff_signal", action.get("type"))
        self.assertEqual("workspace_dashpro", action.get("target_workspace_id"))
        self.assertEqual(
            "signal_monitor_dashpro_sentry_recent_issues_warning",
            action.get("signal_id"),
        )

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    def test_followup_memory_survives_simulated_restart(
        self,
        *_mocks: object,
    ) -> None:
        session = "persist-handoff-session"
        converse_turn(
            content="what's wrong with DashPro?",
            session_id=session,
        )
        clear_memory_cache_for_tests()
        payload = converse_turn(
            content="hand it off",
            session_id=session,
        )
        self.assertEqual("action", payload["turn_kind"])
        action = payload["action"]
        assert isinstance(action, dict)
        self.assertEqual("handoff_signal", action.get("type"))
        self.assertEqual("workspace_dashpro", action.get("target_workspace_id"))

    def test_persisted_turns_reload_after_cache_clear(self) -> None:
        session = "persist-turn-session"
        for index in range(3):
            remember_turn(session, "user", f"turn-{index}")
        clear_memory_cache_for_tests()
        turns = recent_turns(session)
        self.assertEqual(3, len(turns))
        self.assertEqual("turn-0", turns[0]["content"])
        self.assertEqual("turn-2", turns[-1]["content"])

    def test_m1_converse_and_speak_share_session_key(self) -> None:
        session = "kairo:workspace_dashpro:thread_abc"
        self.assertEqual(turn_session_key(session), speak_session_key(session))

    def test_m1_speak_history_scoped_to_shared_session(self) -> None:
        _HISTORY.clear()
        session = "kairo:workspace_dashpro:thread_handoff"
        with patch("app.kairo_voice._try_runtime_line", return_value=None):
            first = generate_spoken_line(
                event_type="conversation_reply",
                session_id=session,
                context={"reply": "DashPro has a Sentry spike, sir."},
            )
            second = generate_spoken_line(
                event_type="agent_start",
                session_id=session,
                context={"operator_prompt": "hand it off"},
            )
        self.assertNotEqual(first["line"], second["line"])
        self.assertEqual(
            len(_HISTORY.get(speak_session_key(session), [])),
            2,
        )

    def test_entity_memory_trimmed_when_over_byte_cap(self) -> None:
        oversized = "x" * 9000
        trimmed_turns, trimmed_entities = _trim_to_byte_cap(
            [],
            {
                "signal_id": oversized,
                "task": oversized,
                "target_workspace_id": "workspace_dashpro",
            },
        )
        self.assertEqual([], trimmed_turns)
        self.assertLess(
            len(
                json.dumps(
                    {"turns": trimmed_turns, "entities": trimmed_entities},
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8"),
            ),
            16 * 1024 + 1,
        )
        self.assertTrue(trimmed_entities)

    def test_lane_b_memory_appendix_includes_entities_and_recent_turns(self) -> None:
        session = "appendix-session"
        remember_entities(
            session,
            signal_title="DashPro payments degraded",
            target_workspace_id="workspace_dashpro",
            task='Investigate signal "DashPro payments degraded"',
        )
        remember_turn(session, "user", "What is going on with DashPro?")
        remember_turn(session, "assistant", "Payments are degraded in DashPro.")
        appendix = build_lane_b_memory_appendix(session, max_chars=800)
        self.assertIn("KAIRO memory", appendix)
        self.assertIn("workspace_dashpro", appendix)
        self.assertIn("DashPro payments degraded", appendix)
        self.assertIn("Recent KAIRO turns:", appendix)
        self.assertLessEqual(len(appendix), 800)

    def test_persisted_entities_reload_after_cache_clear(self) -> None:
        session = "persist-entity-session"
        remember_entities(
            session,
            signal_id="signal_monitor_dashpro_sentry_recent_issues_warning",
            target_workspace_id="workspace_dashpro",
            task='Investigate signal "Sentry spike in DashPro"',
        )
        clear_memory_cache_for_tests()
        entity = entity_context(session)
        self.assertEqual(
            "signal_monitor_dashpro_sentry_recent_issues_warning",
            entity.get("signal_id"),
        )


if __name__ == "__main__":
    unittest.main()
