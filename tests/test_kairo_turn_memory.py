"""OP-C5 turn memory, pack TTL, and DashPro-scoped handoff contracts."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo.context_pack_cache import (  # noqa: E402
    clear_pack_cache_for_tests,
    get_cached_context_pack,
)
from app.kairo.turn_memory import (  # noqa: E402
    clear_memory_for_tests,
    recent_turns,
    remember_turn,
)
from app.kairo_conversation import converse_turn  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
