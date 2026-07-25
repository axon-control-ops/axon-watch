from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo.context_pack_cache import clear_pack_cache_for_tests  # noqa: E402
from app.kairo.turn_memory import clear_memory_for_tests  # noqa: E402
from app.kairo_conversation import converse_turn  # noqa: E402
from app.operator_briefing import build_operator_briefing  # noqa: E402
from app.persistence import run_store  # noqa: E402

_MOCK_BRIEFING = {
    "generated_at": "2026-07-11T00:00:00Z",
    "notice": "Signal pressure is rising.",
    "advise": "Check DashPro evidence before dispatching more work.",
    "top_signals": [
        {
            "signal_id": "signal_dashpro_memory",
            "workspace_id": "workspace_dashpro",
            "title": "DashPro payments degraded",
            "summary": "Open incidents are climbing.",
            "severity": "high",
        }
    ],
    "pending_approvals": {"count": 0, "items": []},
    "active_runs": [],
    "next_safe_actions": [],
    "degraded": {"active": False, "reasons": []},
    "connectivity": {"control_plane_ready": True, "watch_connected": True},
}


class OperatorMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        clear_pack_cache_for_tests()
        clear_memory_for_tests()

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value={"nodes": [], "edges": []})
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value={"items": []})
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    def test_conversation_can_store_and_recall_memory(self, *_mocks) -> None:
        saved = converse_turn(
            content="remember this: DashPro needs explicit approval before payment retries",
            session_id="memory-session",
            workspace_id="workspace_dashpro",
        )
        self.assertIn("saved", saved["reply"].lower())
        self.assertEqual(1, len(saved["artifacts"]))

        recalled = converse_turn(
            content="what did I note about payment retries?",
            session_id="memory-session",
            workspace_id="workspace_dashpro",
        )
        self.assertIn("payment retries", recalled["reply"].lower())
        self.assertGreaterEqual(len(recalled["artifacts"]), 1)

    def test_briefing_surfaces_non_authoritative_memory_highlights(self) -> None:
        converse_turn(
            content="remember this: DashPro payments degrade when retries skip approval",
            session_id="briefing-memory",
            workspace_id="workspace_dashpro",
        )
        with patch(
            "app.operator_briefing.assemble_runtime_summary",
            return_value={
                "generated_at": "2026-07-11T00:00:00Z",
                "watch": {"connected": True},
                "control_plane": {"ready": True},
                "approvals": {"pending_count": 0},
                "degraded": {"active": False, "reasons": []},
                "cli_runtime": {},
            },
        ), patch(
            "app.operator_briefing.build_inbox_response",
            return_value={
                "items": [
                    {
                        "signal_id": "signal_dashpro_memory",
                        "workspace_id": "workspace_dashpro",
                        "title": "DashPro payments degraded",
                        "summary": "Open incidents are climbing.",
                        "severity": "high",
                        "status": "open",
                    }
                ],
                "count": 1,
                "updated_at": "2026-07-11T00:00:00Z",
            },
        ):
            briefing = build_operator_briefing(workspace_id="workspace_dashpro")
        highlights = briefing.get("memory_highlights", [])
        self.assertTrue(highlights)
        self.assertIn("DashPro", str(highlights[0]["content"]))


if __name__ == "__main__":
    unittest.main()

