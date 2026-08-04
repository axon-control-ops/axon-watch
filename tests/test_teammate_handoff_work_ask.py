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

_PASTED_LEAD_ROLLUP = """Lead rollup (Dana) — plan lead-plan-4816b40edb8547c0 still active.

Done: Reviewed Soren run_b29ce3a2af86 / task-bbe0de3a1b0f4104 — status completed but
delivery was no_change (no billing restore, no Vercel push receipt).

Verified in flight: Soren on task-4e1616a270854678 / run_6116c9959326 (strict retry:
Actions billing + Vercel production readiness). Cass Start issued for task-58fecf890e9740e3.

Still open on plan: integrations item task-66ebd55565f44183. Next: wait for receipts.
"""


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

    def test_pasted_lead_rollup_never_materializes_work(self) -> None:
        with patch("app.kairo.teammate_handoff.materialize_lead_fan_out") as materialize:
            action = build_specialty_task_action(
                _PASTED_LEAD_ROLLUP,
                workspace_id="workspace_dashpro",
            )
        self.assertIsNone(action)
        materialize.assert_not_called()


if __name__ == "__main__":
    unittest.main()
