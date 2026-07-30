from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo_conversation import converse_turn  # noqa: E402
from app.kairo_conversation_reply import detect_question_focus  # noqa: E402
from app.kairo_workspace_register_intents import (  # noqa: E402
    is_register_workspace_utterance,
    maybe_handle_register_workspace_intent,
    resolve_known_purpose_workspace_id,
)
from app.kairo.context_pack_cache import clear_pack_cache_for_tests  # noqa: E402
from app.kairo.turn_memory import clear_memory_for_tests  # noqa: E402
from app.workspace_project_bindings import WorkspaceProjectBinding  # noqa: E402


class WorkspaceRegisterIntentTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_pack_cache_for_tests()
        clear_memory_for_tests()

    def test_detects_add_and_convert_utterances(self) -> None:
        self.assertTrue(
            is_register_workspace_utterance(
                "VAXON - add a new workspace Edu Pro for aftercare synced with DashPro"
            )
        )
        self.assertTrue(
            is_register_workspace_utterance(
                "convert the least used Workspace to Edu Pro"
            )
        )
        self.assertFalse(is_register_workspace_utterance("are all workspaces healthy?"))
        self.assertFalse(
            is_register_workspace_utterance(
                "Lindi, what's the aftercare lead plan status?"
            )
        )
        self.assertFalse(is_register_workspace_utterance("tell me about Edu Pro aftercare"))
        self.assertTrue(
            is_register_workspace_utterance("assign aftercare to the school workspace")
        )

    def test_edu_pro_maps_to_school_of_excellence(self) -> None:
        self.assertEqual(
            "workspace_edudashpro_school",
            resolve_known_purpose_workspace_id("Edu Pro"),
        )
        self.assertEqual(
            "workspace_edudashpro_school",
            resolve_known_purpose_workspace_id("aftercare"),
        )
        self.assertEqual(
            "workspace_edudashpro_school",
            resolve_known_purpose_workspace_id("preschool"),
        )

    def test_sync_with_edudash_pro_means_dashpro_app(self) -> None:
        from app.kairo_workspace_register_intents import extract_sync_peer_workspace_id

        self.assertEqual(
            "workspace_dashpro",
            extract_sync_peer_workspace_id("in sync with EduDash Pro"),
        )
        self.assertEqual(
            "workspace_dashpro",
            extract_sync_peer_workspace_id("synced with DashPro workspace"),
        )

    def test_fleet_focus_skips_register_utterances(self) -> None:
        self.assertEqual(
            "general",
            detect_question_focus(
                "add a new workspace Edu Pro synced with DashPro",
                recent_user_turns=[],
            ),
        )
        self.assertEqual(
            "fleet",
            detect_question_focus("are all workspaces healthy?", recent_user_turns=[]),
        )

    def test_assign_edu_pro_opens_school_workspace(self) -> None:
        school = WorkspaceProjectBinding(
            workspace_id="workspace_edudashpro_school",
            project_root=Path(tempfile.mkdtemp()),
            display_name="EduDash PRO School of Excellence",
        )
        with patch(
            "app.kairo_workspace_register_intents.get_workspace_project_binding",
            return_value=school,
        ):
            payload = maybe_handle_register_workspace_intent(
                content=(
                    "VAXON - can we please convert the least used Workspace - to Edu Pro "
                    "- aftercare in sync with DashPro workspace"
                ),
                guest_name=None,
            )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual("action", payload["turn_kind"])
        self.assertIn("EduDash PRO School of Excellence", str(payload["reply"]))
        reply = str(payload["reply"]).lower()
        self.assertIn("grade 1–7", reply)
        self.assertIn("literate", reply)
        self.assertEqual(
            {
                "type": "switch_workspace",
                "workspace_id": "workspace_edudashpro_school",
            },
            payload["action"],
        )
        self.assertNotIn("look green", str(payload["reply"]).lower())

    @patch("app.kairo_conversation.build_operator_brain_graph", return_value={"nodes": [], "edges": []})
    @patch(
        "app.kairo_conversation.build_operator_fleet_health",
        return_value={"items": [], "critical_count": 0, "attention_count": 0, "workspace_count": 3},
    )
    @patch(
        "app.kairo_conversation.build_operator_briefing",
        return_value={
            "generated_at": "2026-07-27T00:00:00Z",
            "notice": "",
            "advise": "",
            "top_signals": [],
            "pending_approvals": {"count": 0, "items": []},
            "active_runs": [],
            "degraded": {"active": False, "reasons": []},
            "cli_runtime": {"dispatch_ready": True, "blockers": []},
        },
    )
    def test_converse_turn_does_not_return_fleet_green_for_edu_pro(self, *_mocks: object) -> None:
        school = WorkspaceProjectBinding(
            workspace_id="workspace_edudashpro_school",
            project_root=Path(tempfile.mkdtemp()),
            display_name="EduDash PRO School of Excellence",
        )
        with patch(
            "app.kairo_workspace_register_intents.get_workspace_project_binding",
            return_value=school,
        ):
            payload = converse_turn(
                content=(
                    "VAXON - add Edu Pro workspace for aftercare and keep it in sync "
                    "with DashPro"
                ),
                session_id="test-edu-pro-assign",
            )
        self.assertEqual("action", payload["turn_kind"])
        self.assertNotIn("look green", str(payload["reply"]).lower())
        self.assertEqual(
            "workspace_edudashpro_school",
            (payload.get("action") or {}).get("workspace_id"),
        )


if __name__ == "__main__":
    unittest.main()
