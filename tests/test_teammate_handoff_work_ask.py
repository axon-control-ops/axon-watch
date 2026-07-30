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


if __name__ == "__main__":
    unittest.main()
