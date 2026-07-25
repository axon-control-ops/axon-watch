from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo_conversation import converse_turn  # noqa: E402

_MOCK_BRIEFING = {
    "generated_at": "2026-07-08T00:00:00Z",
    "notice": "Two runs are active.",
    "advise": "Review the top signal before dispatching more work.",
    "top_signals": [],
    "pending_approvals": {"count": 0, "items": []},
    "active_runs": [],
    "degraded": {"active": False, "reasons": []},
}
_MOCK_FLEET = {"items": []}
_MOCK_GRAPH = {"nodes": [{"node_id": "n1"}], "edges": []}


class KairoConversationSmalltalkTests(unittest.TestCase):
    @patch("app.kairo_conversation.build_operator_brain_graph", return_value=_MOCK_GRAPH)
    @patch("app.kairo_conversation.build_operator_fleet_health", return_value=_MOCK_FLEET)
    @patch("app.kairo_conversation.build_operator_briefing", return_value=_MOCK_BRIEFING)
    def test_converse_self_intro_returns_vaxon_identity(self, *_mocks: object) -> None:
        payload = converse_turn(content="tell me about yourself", session_id="intro-session")
        self.assertEqual("open_question", payload["turn_kind"])
        self.assertIn("VAXON", str(payload["reply"]))
        self.assertRegex(str(payload["reply"]).lower(), r"runtime|control plane|workspace")


if __name__ == "__main__":
    unittest.main()

