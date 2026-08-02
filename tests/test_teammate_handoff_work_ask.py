from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo.teammate_handoff import (  # noqa: E402
    _LEAD_DECOMPOSE_HINT_RE,
    _TASK_REQUEST_RE,
    build_specialty_task_action,
    is_identity_charter_text,
    is_mission_spec_text,
)
from app.kairo_conversation_reply import detect_question_focus  # noqa: E402

_OPERATOR_ASK = (
    "VAXON check DashPro workspace and help me out - I need the new code "
    "pushed to Canary runtime - with the dashboard fixes and the graduation work"
)


class TeammateHandoffWorkAskTests(unittest.TestCase):
    def test_task_verbs_include_fixes_push_and_help_me(self) -> None:
        self.assertIsNotNone(_TASK_REQUEST_RE.search("dashboard fixes"))
        self.assertIsNotNone(_TASK_REQUEST_RE.search("pushed to Canary"))
        self.assertIsNotNone(_TASK_REQUEST_RE.search("help me out"))
        self.assertIsNotNone(_TASK_REQUEST_RE.search(_OPERATOR_ASK))

    def test_multi_work_ask_is_lead_decompose_hint(self) -> None:
        self.assertIsNotNone(_LEAD_DECOMPOSE_HINT_RE.search(_OPERATOR_ASK))
        self.assertIsNotNone(
            _LEAD_DECOMPOSE_HINT_RE.search("push the new code to canary for DashPro")
        )

    def test_canary_runtime_is_not_cli_runtime_focus(self) -> None:
        self.assertNotEqual(
            detect_question_focus(_OPERATOR_ASK, recent_user_turns=[]),
            "runtime",
        )
        self.assertEqual(
            detect_question_focus(
                "is the CLI runtime dispatch-ready?",
                recent_user_turns=[],
            ),
            "runtime",
        )

    def test_operator_multi_work_ask_materializes_lead_fan_out(self) -> None:
        fake = {
            "mode": "decompose",
            "tasks": [{"task_id": "t1"}, {"task_id": "t2"}],
            "runs": [],
            "deferred": [],
            "receipt": {"ok": True},
            "plan": {"plan_id": "plan_1"},
        }
        with patch(
            "app.kairo.teammate_handoff.materialize_lead_fan_out",
            return_value=fake,
        ):
            action = build_specialty_task_action(
                _OPERATOR_ASK,
                workspace_id="workspace_dashpro",
            )
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action["type"], "lead_fan_out")
        self.assertEqual(action["target_workspace_id"], "workspace_dashpro")
        self.assertEqual(action["mode"], "decompose")
        self.assertEqual(len(action["tasks"]), 2)

    def test_identity_charter_with_incidental_task_verbs_never_routes(self) -> None:
        charter = (
            "# VAXON\n"
            "You are VAXON, the Executive Operating System.\n"
            "Chief of Staff\n"
            "Core Principles\n"
            "Evidence before assumption. Architecture before implementation.\n"
            "Never perform specialist implementation yourself. Investigate uncertainty.\n"
            "Non-Negotiable Rules\n"
            "Never fabricate evidence. Continue improving architecture.\n"
            "Autonomy Levels\n"
            "Observe, research, document, plan, delegate, approve reversible work.\n"
            "First Directive\n"
            "Study the architecture before changing it.\n"
        ) * 3

        self.assertTrue(is_identity_charter_text(charter))
        with patch(
            "app.kairo.teammate_handoff.route_teammate_decision"
        ) as route:
            action = build_specialty_task_action(
                charter,
                workspace_id="workspace_axon_watch",
            )

        self.assertIsNone(action)
        route.assert_not_called()

    def test_mission_spec_prefers_lead_fan_out_and_attaches_spec(self) -> None:
        mission = (
            "Mission Title: Authentication launch\n"
            "Objective: Build the login UI and session API\n"
            "Deliverables: Frontend and backend implementation\n"
            "Evidence Required: Tests and CI receipts"
        )
        fake = {
            "plan_id": "lead-plan-auth",
            "mode": "decompose",
            "tasks": [{"task_id": "frontend"}, {"task_id": "backend"}],
            "runs": [],
            "deferred": [],
            "receipt": {"ok": True},
            "plan": {
                "items": [
                    {"goal": "Build login UI", "owner_role": "frontend"},
                    {"goal": "Build session API", "owner_role": "backend"},
                ]
            },
        }

        self.assertTrue(is_mission_spec_text(mission))
        with patch(
            "app.kairo.teammate_handoff.materialize_lead_fan_out",
            return_value=fake,
        ) as materialize:
            action = build_specialty_task_action(
                mission,
                workspace_id="workspace_axon_watch",
            )

        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual("lead_fan_out", action["type"])
        self.assertEqual("lead-plan-auth", action["mission_spec"]["mission_id"])
        self.assertIn("frontend", action["mission_spec"]["recommended_specialists"])
        materialize.assert_called_once()


if __name__ == "__main__":
    unittest.main()
