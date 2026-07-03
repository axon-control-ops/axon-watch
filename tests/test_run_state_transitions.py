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

    def test_allowed_bootstrap_transitions(self) -> None:
        self.assertTrue(can_transition("queued", "starting"))
        self.assertTrue(can_transition("starting", "executing"))
        self.assertTrue(can_transition("executing", "completed"))

    def test_disallowed_transitions(self) -> None:
        self.assertFalse(can_transition("queued", "executing"))
        self.assertFalse(can_transition("completed", "executing"))
        self.assertFalse(can_transition("executing", "queued"))


if __name__ == "__main__":
    unittest.main()
