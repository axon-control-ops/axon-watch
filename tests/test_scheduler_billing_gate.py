"""Billing/credits auto-start gate for continuous worker ticks.

Regression coverage for the retry-storm bug: a role whose last shift failed
on billing (e.g. "Credit balance is too low", "unpaid invoice") was not
recognized by either the usage-limit or runtime-auth gates, so the scheduler
kept re-dispatching it every 45s tick indefinitely — full system prompt and
a real model turn each time, for as long as the account stayed unpaid.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.scheduler_auto_start_gates import (  # noqa: E402
    billing_blocks_auto_start,
)


class BillingGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.state_dir.cleanup)
        self.state_path = Path(self.state_dir.name) / "billing-retry-cooldown.json"

    def test_non_billing_failure_does_not_block(self) -> None:
        with patch(
            "app.workspace_agents.scheduler_auto_start_gates.latest_role_run_outcome",
            return_value={
                "run_id": "run_1",
                "outcome": "failed",
                "detail": "verify:contracts — assertion failed",
            },
        ):
            blocked = billing_blocks_auto_start(
                "workspace_dashpro", "backend", state_path=self.state_path
            )
        self.assertFalse(blocked)

    def test_successful_last_run_does_not_block(self) -> None:
        with patch(
            "app.workspace_agents.scheduler_auto_start_gates.latest_role_run_outcome",
            return_value={"run_id": "run_1", "outcome": "completed", "detail": ""},
        ):
            blocked = billing_blocks_auto_start(
                "workspace_dashpro", "backend", state_path=self.state_path
            )
        self.assertFalse(blocked)

    def test_billing_failure_blocks_and_persists_cooldown_start(self) -> None:
        now = datetime.now(timezone.utc)
        with patch(
            "app.workspace_agents.scheduler_auto_start_gates.latest_role_run_outcome",
            return_value={
                "run_id": "run_1",
                "outcome": "failed",
                "detail": "Credit balance is too low",
            },
        ):
            blocked = billing_blocks_auto_start(
                "workspace_dashpro", "backend", now=now, state_path=self.state_path
            )
        self.assertTrue(blocked)
        self.assertTrue(self.state_path.is_file())

    def test_stays_blocked_within_cooldown_window_on_same_failed_run(self) -> None:
        start = datetime.now(timezone.utc)
        with patch(
            "app.workspace_agents.scheduler_auto_start_gates.latest_role_run_outcome",
            return_value={
                "run_id": "run_1",
                "outcome": "failed",
                "detail": "Credit balance is too low",
            },
        ):
            first = billing_blocks_auto_start(
                "workspace_dashpro", "backend", now=start, state_path=self.state_path
            )
            later = billing_blocks_auto_start(
                "workspace_dashpro",
                "backend",
                now=start + timedelta(minutes=10),
                state_path=self.state_path,
            )
        self.assertTrue(first)
        self.assertTrue(later, "same failed run within the cooldown window must stay blocked")

    def test_soft_opens_after_cooldown_window_elapses(self) -> None:
        start = datetime.now(timezone.utc)
        with patch(
            "app.workspace_agents.scheduler_auto_start_gates.latest_role_run_outcome",
            return_value={
                "run_id": "run_1",
                "outcome": "failed",
                "detail": "Credit balance is too low",
            },
        ):
            billing_blocks_auto_start(
                "workspace_dashpro", "backend", now=start, state_path=self.state_path
            )
            still_blocked_after_29_min = billing_blocks_auto_start(
                "workspace_dashpro",
                "backend",
                now=start + timedelta(minutes=29),
                state_path=self.state_path,
            )
            open_after_31_min = billing_blocks_auto_start(
                "workspace_dashpro",
                "backend",
                now=start + timedelta(minutes=31),
                state_path=self.state_path,
            )
        self.assertTrue(still_blocked_after_29_min)
        self.assertFalse(
            open_after_31_min,
            "gate must eventually retry on its own once the cooldown window passes, "
            "rather than requiring a manual unblock",
        )

    def test_new_failed_run_restarts_cooldown(self) -> None:
        """A fresh attempt (new run_id) after the cooldown gets its own fresh window."""
        start = datetime.now(timezone.utc)
        with patch(
            "app.workspace_agents.scheduler_auto_start_gates.latest_role_run_outcome",
            return_value={
                "run_id": "run_1",
                "outcome": "failed",
                "detail": "Credit balance is too low",
            },
        ):
            billing_blocks_auto_start(
                "workspace_dashpro", "backend", now=start, state_path=self.state_path
            )

        with patch(
            "app.workspace_agents.scheduler_auto_start_gates.latest_role_run_outcome",
            return_value={
                "run_id": "run_2",
                "outcome": "failed",
                "detail": "Credit balance is too low",
            },
        ):
            blocked = billing_blocks_auto_start(
                "workspace_dashpro",
                "backend",
                now=start + timedelta(minutes=31),
                state_path=self.state_path,
            )
        self.assertTrue(blocked, "a new failed attempt should start its own cooldown")


if __name__ == "__main__":
    unittest.main()
