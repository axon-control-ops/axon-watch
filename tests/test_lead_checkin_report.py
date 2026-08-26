"""Lead check-in message formatting: the :::decision fence must stay intact.

format_lead_checkin_message() used to run the *entire* finding detail
(including an embedded :::decision fence) through humanize_lead_failure_detail,
which collapses all whitespace to a single line — breaking the fence's
line-exact ':::decision' / ':::' markers that the frontend parser requires.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.lead_checkin_assign import LeadCheckinFinding  # noqa: E402
from app.workspace_agents.lead_checkin_report import format_lead_checkin_message  # noqa: E402
from app.workspace_agents.lead_failure_diagnosis import diagnose_lead_failure  # noqa: E402
from app.workspace_agents.recovery_decision import (  # noqa: E402
    decision_from_payload,
    render_decision_fence,
)

import json


class DecisionFenceSurvivesFormattingTests(unittest.TestCase):
    def _finding_with_decision(self) -> LeadCheckinFinding:
        decision = diagnose_lead_failure(
            workspace_id="workspace_demo",
            run_id="run_abc",
            detail="Cursor CLI is not signed in",
        )
        detail = (
            "Cursor CLI is not signed in [run=run_abc] Lead roles must not "
            "remain stuck in Error; VAXON should triage the control-plane/runtime "
            "cause or ask the operator." + render_decision_fence(decision)
        )
        return LeadCheckinFinding(
            kind="operator_blocker",
            workspace_id="workspace_demo",
            owner_role="watcher",
            title="Mira (lead) last shift failed",
            detail=detail,
            dedupe_key="failed_shift:workspace_demo:lead",
            escalate_only=True,
        )

    def test_fence_lines_are_not_collapsed_by_humanization(self) -> None:
        message = format_lead_checkin_message([self._finding_with_decision()], [])
        lines = message.splitlines()
        self.assertIn(":::decision", lines)
        self.assertIn(":::", lines[lines.index(":::decision") + 2 :][:1] or [])

    def test_fence_json_round_trips_out_of_the_rendered_message(self) -> None:
        message = format_lead_checkin_message([self._finding_with_decision()], [])
        lines = message.splitlines()
        fence_start = lines.index(":::decision")
        body_line = lines[fence_start + 1]
        self.assertEqual(":::", lines[fence_start + 2])
        payload = json.loads(body_line)
        restored = decision_from_payload(payload)
        self.assertEqual("blocked", restored.card_type)
        self.assertEqual("runtime_auth", restored.classification)
        self.assertEqual((), restored.choices)

    def test_prose_detail_is_still_humanized(self) -> None:
        message = format_lead_checkin_message([self._finding_with_decision()], [])
        self.assertIn("not signed in", message.lower())


if __name__ == "__main__":
    unittest.main()
