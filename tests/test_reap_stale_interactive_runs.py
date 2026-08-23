"""Abandoned interactive (non-employee) runs must resolve without a restart.

Regression guard: the employee reaper correctly skips untagged runs (an
operator composer turn can legitimately run long), but nothing else revisited
them if genuinely abandoned. A run could sit `executing` indefinitely after a
closed tab or dropped connection, and the only code that could resolve it
(interrupt_run_on_restart) ran once, at process boot.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.runs.stale_reconcile import reap_stale_interactive_runs


def _record(**overrides):
    base = {
        "run_id": "run_x",
        "employee_role": None,
        "phase": "executing",
        "history_ref": "history/run_x",
        "started_at": "2026-08-21T00:00:00Z",
    }
    base.update(overrides)
    return base


class ReapStaleInteractiveRunsTests(unittest.TestCase):
    def _now(self, minutes: float) -> datetime:
        return datetime(2026, 8, 21, 0, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=minutes)

    def test_executing_run_past_the_cutoff_is_failed(self) -> None:
        with patch(
            "app.persistence.run_store.list_runs", return_value=[_record(phase="executing")]
        ), patch(
            "app.runs.stale_reconcile._last_meaningful_transition_timestamp", return_value=None
        ), patch("app.runs.service.fail_run") as fail_run:
            reaped = reap_stale_interactive_runs(now=self._now(45), stale_seconds=1800)
        self.assertEqual(reaped, ["run_x"])
        fail_run.assert_called_once()

    def test_employee_runs_are_never_touched_here(self) -> None:
        # This reaper is only for the untagged runs the employee reaper skips.
        with patch(
            "app.persistence.run_store.list_runs",
            return_value=[_record(employee_role="frontend")],
        ), patch("app.runs.service.fail_run") as fail_run:
            reaped = reap_stale_interactive_runs(now=self._now(45), stale_seconds=1800)
        self.assertEqual(reaped, [])
        fail_run.assert_not_called()

    def test_recent_run_is_left_alone(self) -> None:
        with patch(
            "app.persistence.run_store.list_runs", return_value=[_record(phase="executing")]
        ), patch(
            "app.runs.stale_reconcile._last_meaningful_transition_timestamp", return_value=None
        ), patch("app.runs.service.fail_run") as fail_run:
            reaped = reap_stale_interactive_runs(now=self._now(5), stale_seconds=1800)
        self.assertEqual(reaped, [])
        fail_run.assert_not_called()

    def test_awaiting_approval_past_cutoff_is_cancelled_not_failed(self) -> None:
        with patch(
            "app.persistence.run_store.list_runs",
            return_value=[_record(phase="awaiting_approval")],
        ), patch(
            "app.runs.stale_reconcile._last_meaningful_transition_timestamp", return_value=None
        ), patch("app.runs.service._transition_record") as transition, patch(
            "app.runs.service.fail_run"
        ) as fail_run:
            reaped = reap_stale_interactive_runs(now=self._now(45), stale_seconds=1800)
        self.assertEqual(reaped, ["run_x"])
        fail_run.assert_not_called()
        transition.assert_called_once()
        self.assertEqual(transition.call_args.kwargs["to_phase"], "cancelled")

    def test_terminal_and_review_ready_runs_are_never_candidates(self) -> None:
        for phase in ("completed", "failed", "cancelled", "review_ready"):
            with self.subTest(phase=phase):
                with patch(
                    "app.persistence.run_store.list_runs", return_value=[_record(phase=phase)]
                ), patch("app.runs.service.fail_run") as fail_run:
                    reaped = reap_stale_interactive_runs(now=self._now(9999), stale_seconds=60)
                self.assertEqual(reaped, [])
                fail_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
