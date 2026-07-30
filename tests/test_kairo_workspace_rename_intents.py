from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo_conversation import converse_turn  # noqa: E402
from app.kairo_workspace_rename_intents import (  # noqa: E402
    extract_rename_display_name,
    is_rename_workspace_utterance,
    maybe_handle_rename_workspace_intent,
)
from app.kairo.context_pack_cache import clear_pack_cache_for_tests  # noqa: E402
from app.kairo.turn_memory import clear_memory_for_tests  # noqa: E402
from app.workspace_project_bindings import WorkspaceProjectBinding  # noqa: E402


class WorkspaceRenameIntentTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_pack_cache_for_tests()
        clear_memory_for_tests()

    def test_detects_rename_utterance(self) -> None:
        self.assertTrue(
            is_rename_workspace_utterance("VAXON - change the name to EDP Excellence")
        )
        self.assertEqual(
            "EDP Excellence",
            extract_rename_display_name("change the name to EDP Excellence"),
        )

    def test_rename_updates_binding_display_name(self) -> None:
        root = Path(tempfile.mkdtemp())
        bindings_file = root / "bindings.json"
        bindings_file.write_text(
            json.dumps(
                {
                    "bindings": {
                        "workspace_edudashpro_school": {
                            "display_name": "EduDash PRO School of Excellence",
                            "project_root": str(root),
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        school = WorkspaceProjectBinding(
            workspace_id="workspace_edudashpro_school",
            project_root=root,
            display_name="EduDash PRO School of Excellence",
        )
        with (
            patch(
                "app.kairo_workspace_rename_intents.get_workspace_project_binding",
                return_value=school,
            ),
            patch(
                "app.kairo_workspace_rename_intents.upsert_workspace_project_binding",
            ) as upsert,
            patch(
                "app.kairo_workspace_rename_intents._update_agents_company_name",
            ),
            patch(
                "app.kairo_workspace_rename_intents._update_frontend_canonical_label",
            ),
        ):
            upsert.return_value = WorkspaceProjectBinding(
                workspace_id="workspace_edudashpro_school",
                project_root=root,
                display_name="EDP Excellence",
            )
            payload = maybe_handle_rename_workspace_intent(
                content="VAXON - change the name to EDP Excellence",
                workspace_id="workspace_edudashpro_school",
                guest_name=None,
            )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertIn("EDP Excellence", str(payload["reply"]))
        self.assertEqual(
            {
                "type": "switch_workspace",
                "workspace_id": "workspace_edudashpro_school",
            },
            payload["action"],
        )
        upsert.assert_called_once()
        kwargs = upsert.call_args.kwargs
        self.assertEqual("EDP Excellence", kwargs["display_name"])

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
    def test_converse_turn_rename_via_vaxon(self, *_mocks: object) -> None:
        root = Path(tempfile.mkdtemp())
        school = WorkspaceProjectBinding(
            workspace_id="workspace_edudashpro_school",
            project_root=root,
            display_name="EduDash PRO School of Excellence",
        )
        with (
            patch(
                "app.kairo_workspace_rename_intents.get_workspace_project_binding",
                return_value=school,
            ),
            patch(
                "app.kairo_workspace_rename_intents.upsert_workspace_project_binding",
                return_value=WorkspaceProjectBinding(
                    workspace_id="workspace_edudashpro_school",
                    project_root=root,
                    display_name="EDP Excellence",
                ),
            ),
            patch("app.kairo_workspace_rename_intents._update_agents_company_name"),
            patch("app.kairo_workspace_rename_intents._update_frontend_canonical_label"),
        ):
            payload = converse_turn(
                content="VAXON - change the name to EDP Excellence",
                session_id="test-rename-edp",
                workspace_id="workspace_edudashpro_school",
            )
        self.assertEqual("action", payload["turn_kind"])
        self.assertIn("EDP Excellence", str(payload["reply"]))
        self.assertNotIn("look green", str(payload["reply"]).lower())


if __name__ == "__main__":
    unittest.main()
