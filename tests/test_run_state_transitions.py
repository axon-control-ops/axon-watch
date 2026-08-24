from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.domain.run_state import (  # noqa: E402
    capability_flags,
    is_terminal_phase,
    status_for_phase,
)
from app.domain.run_transitions import can_transition  # noqa: E402


class RunStateTransitionTests(unittest.TestCase):
    def test_status_for_phase_maps_executing_to_running(self) -> None:
        self.assertEqual("running", status_for_phase("executing"))

    def test_status_for_phase_maps_completed_to_done(self) -> None:
        self.assertEqual("done", status_for_phase("completed"))

    def test_terminal_phases_are_recognized(self) -> None:
        for phase in ("completed", "failed", "cancelled"):
            self.assertTrue(is_terminal_phase(phase))
        self.assertFalse(is_terminal_phase("executing"))

    def test_capability_flags_for_executing(self) -> None:
        flags = capability_flags("executing")
        self.assertTrue(flags["can_stop"])
        self.assertFalse(flags["can_resume"])
        self.assertFalse(flags["can_approve"])
        self.assertFalse(flags["can_review"])

    def test_capability_flags_for_awaiting_approval(self) -> None:
        flags = capability_flags("awaiting_approval")
        self.assertTrue(flags["can_stop"])
        self.assertFalse(flags["can_resume"])
        self.assertTrue(flags["can_approve"])
        self.assertFalse(flags["can_review"])

    def test_capability_flags_for_review_ready(self) -> None:
        flags = capability_flags("review_ready")
        self.assertFalse(flags["can_stop"])
        self.assertTrue(flags["can_resume"])
        self.assertFalse(flags["can_approve"])
        self.assertTrue(flags["can_review"])

    def test_allowed_bootstrap_transitions(self) -> None:
        self.assertTrue(can_transition("queued", "starting"))
        self.assertTrue(can_transition("starting", "executing"))
        self.assertTrue(can_transition("executing", "completed"))
        self.assertTrue(can_transition("paused", "executing"))
        self.assertTrue(can_transition("paused", "completed"))

    def test_stop_to_paused_transitions_match_accepted_amendment(self) -> None:
        for phase in ("queued", "starting", "planning", "executing", "waiting_external"):
            self.assertTrue(can_transition(phase, "paused"))

    def test_approval_transitions_follow_frozen_contract(self) -> None:
        self.assertTrue(can_transition("planning", "awaiting_approval"))
        self.assertTrue(can_transition("executing", "awaiting_approval"))
        self.assertTrue(can_transition("awaiting_approval", "executing"))
        self.assertTrue(can_transition("awaiting_approval", "cancelled"))

    def test_review_ready_transitions_follow_frozen_contract(self) -> None:
        self.assertTrue(can_transition("executing", "review_ready"))
        self.assertTrue(can_transition("review_ready", "completed"))
        self.assertTrue(can_transition("review_ready", "executing"))

    def test_every_phase_fail_run_accepts_can_reach_failed(self) -> None:
        """fail_run() accepts executing/review_ready/paused as input phases.

        Regression: the table only allowed executing -> failed, so failing a
        paused or review_ready run raised RunLifecycleError inside
        _transition_record. fail_worker_run swallows that error, leaving the
        run stuck in a non-terminal phase forever instead of failing cleanly.
        """
        for phase in ("executing", "review_ready", "paused"):
            with self.subTest(phase=phase):
                self.assertTrue(can_transition(phase, "failed"))

    def test_terminal_phases_still_cannot_be_failed(self) -> None:
        for phase in ("completed", "failed", "cancelled"):
            with self.subTest(phase=phase):
                self.assertFalse(can_transition(phase, "failed"))

    def test_disallowed_transitions(self) -> None:
        self.assertFalse(can_transition("queued", "executing"))
        self.assertFalse(can_transition("completed", "executing"))
        self.assertFalse(can_transition("executing", "queued"))


if __name__ == "__main__":
    unittest.main()
