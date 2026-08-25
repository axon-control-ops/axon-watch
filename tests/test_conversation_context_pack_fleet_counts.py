from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


class ConversationContextPackFleetCountTests(unittest.TestCase):
    def test_counts_current_health_field_and_legacy_tone_field(self) -> None:
        from app.kairo.conversation_context_pack import build_conversation_context_pack_uncached

        briefing = {"scope": {"workspace_id": "workspace_axon_watch"}}
        fleet = {
            "items": [
                {"workspace_id": "one", "health": "critical"},
                {"workspace_id": "two", "health": "attention"},
                {"workspace_id": "three", "tone": "attention"},
            ]
        }
        with patch(
            "app.kairo.conversation_context_pack.build_operator_briefing",
            return_value=briefing,
        ), patch(
            "app.kairo.conversation_context_pack.build_operator_fleet_health",
            return_value=fleet,
        ), patch(
            "app.kairo.conversation_context_pack.build_operator_brain_graph",
            return_value={"nodes": [], "edges": []},
        ), patch(
            "app.kairo.conversation_context_pack.recent_workspace_dialogue",
            return_value=[],
        ):
            pack = build_conversation_context_pack_uncached(workspace_id=None)

        self.assertEqual(1, pack["fleet"]["critical_count"])
        self.assertEqual(2, pack["fleet"]["attention_count"])


if __name__ == "__main__":
    unittest.main()
