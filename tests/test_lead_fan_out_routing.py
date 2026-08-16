"""A Lead's fan-out brief must not collapse onto one specialist."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.lead_task_plan import detect_fan_out_intent  # noqa: E402
from app.workspace_agents.teammate_route import route_teammate_decision  # noqa: E402

BRIEF = """Discovery pass on the teachers dashboard - read-only, no code changes.
Fan this out with axon-assign; do not write a handoff doc instead of dispatching.
Priya (frontend): audit the render path.
Cass (watcher): run the three existing suites.
Dana: rollup only."""


class FanOutVocabularyTests(unittest.TestCase):
    def test_the_wording_leads_are_told_to_use_is_recognised(self) -> None:
        # Regression: the guard existed but did not know "fan out" or the tool
        # name the lead prompt tells the Lead to call.
        for text in (
            "Fan this out with axon-assign; do not write a handoff doc",
            "fan out the teachers dashboard work",
            "Use axon-assign to dispatch this",
            "fanning this out to the team",
        ):
            with self.subTest(text=text):
                self.assertTrue(detect_fan_out_intent(text))

    def test_ordinary_single_assignments_are_not_swept_up(self) -> None:
        for text in (
            "Priya, fix the teacher dashboard layout",
            "Add a lessons service unit test",
        ):
            with self.subTest(text=text):
                self.assertFalse(detect_fan_out_intent(text))


class MultiNameRoutingTests(unittest.TestCase):
    def test_brief_naming_several_teammates_stays_with_the_lead(self) -> None:
        decision = route_teammate_decision(
            workspace_id="workspace_dashpro",
            prompt=BRIEF,
            use_model_tiebreak=False,
        )
        self.assertFalse(decision.should_route)
        self.assertEqual("lead_fan_out", decision.reason)

    def test_single_named_assignment_still_routes(self) -> None:
        decision = route_teammate_decision(
            workspace_id="workspace_dashpro",
            prompt="Priya, please fix the teacher dashboard header layout",
            use_model_tiebreak=False,
        )
        self.assertTrue(decision.should_route)

    def test_multi_name_guard_holds_without_fan_out_wording(self) -> None:
        decision = route_teammate_decision(
            workspace_id="workspace_dashpro",
            prompt="Priya audits the render path, Marco checks the API filters.",
            use_model_tiebreak=False,
        )
        self.assertFalse(decision.should_route)


if __name__ == "__main__":
    unittest.main()
