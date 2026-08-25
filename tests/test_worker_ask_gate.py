"""Unresolved operator asks must hold the run, not let it run on."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app.domain.run_transitions import can_transition
from app.runs.service import block_run_on_operator_ask


class AskGateTransitionTests(unittest.TestCase):
    def test_executing_can_be_held_and_released_through_approve(self) -> None:
        # The hold must land in a phase the operator can actually release,
        # otherwise answering the ask would strand the run.
        self.assertTrue(can_transition("executing", "awaiting_approval"))
        self.assertTrue(can_transition("awaiting_approval", "executing"))

    def test_finished_runs_are_never_dragged_back_into_blocked(self) -> None:
        for phase in ("completed", "failed", "cancelled"):
            self.assertFalse(can_transition(phase, "awaiting_approval"))

    def test_block_returns_none_for_an_unholdable_phase(self) -> None:
        with patch("app.runs.service.run_store.get_run", return_value={"phase": "completed"}):
            self.assertIsNone(block_run_on_operator_ask("run-1", prompt="pick one"))

    def test_block_records_the_question_on_the_run(self) -> None:
        record = {"phase": "executing", "history_ref": "h1"}
        captured: dict[str, object] = {}

        def fake_transition(rec, **kwargs):
            captured.update(kwargs)
            return {**rec, "phase": kwargs["to_phase"], "current_step": kwargs["current_step"]}

        with patch("app.runs.service.run_store.get_run", return_value=record), patch(
            "app.runs.service._transition_record", side_effect=fake_transition
        ), patch("app.runs.run_material_change.notify_run_material_change"):
            blocked = block_run_on_operator_ask("run-1", prompt="Which scope for item 2?")

        self.assertEqual(blocked["phase"], "awaiting_approval")
        self.assertIn("Which scope for item 2?", captured["current_step"])


if __name__ == "__main__":
    unittest.main()
