"""Generic escalating-backoff gate for continuous worker ticks.

Regression coverage for the "stuck agents" pattern found live: a role whose
last shift failed on something none of the specific gates recognize (a CLI
self-update race, a transient recursion bug, any error nobody wrote a
dedicated gate for) was retried on every 45s scheduler tick indefinitely —
full system prompt and a real dispatch each time, forever, until the
underlying issue happened to clear on its own.
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
    generic_repeated_failure_blocks_auto_start,
)

_PATCH_TARGET = "app.workspace_agents.scheduler_auto_start_gates.latest_role_run_outcome"


class GenericRetryBackoffGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.state_dir.cleanup)
        self.state_path = Path(self.state_dir.name) / "generic-retry-cooldown.json"

    def test_successful_last_run_does_not_block(self) -> None:
        with patch(_PATCH_TARGET, return_value={"run_id": "run_1", "outcome": "completed", "detail": ""}):
            blocked = generic_repeated_failure_blocks_auto_start(
                "workspace_dashpro", "watcher", state_path=self.state_path
            )
        self.assertFalse(blocked)

    def test_already_classified_failures_defer_to_their_own_gates(self) -> None:
        for detail in (
            "Out of usage — increase limits in Cursor",
            "Credit balance is too low",
            "ActionRequiredError: You have an unpaid invoice",
            "Cursor is installed but not signed in. Run `cursor agent login` or unlock /vault.",
        ):
            with patch(
                _PATCH_TARGET,
                return_value={"run_id": "run_1", "outcome": "failed", "detail": detail},
            ):
                blocked = generic_repeated_failure_blocks_auto_start(
                    "workspace_dashpro", "watcher", state_path=self.state_path
                )
            self.assertFalse(blocked, f"should not double-gate an already-classified failure: {detail}")

    def test_unclassified_failure_blocks_and_persists(self) -> None:
        now = datetime.now(timezone.utc)
        with patch(
            _PATCH_TARGET,
            return_value={
                "run_id": "run_1",
                "outcome": "failed",
                "detail": "Error: Could not install cursor-agent.",
            },
        ):
            blocked = generic_repeated_failure_blocks_auto_start(
                "workspace_dashpro", "watcher", now=now, state_path=self.state_path
            )
        self.assertTrue(blocked)
        self.assertTrue(self.state_path.is_file())

    def test_stays_blocked_within_first_backoff_window(self) -> None:
        start = datetime.now(timezone.utc)
        with patch(
            _PATCH_TARGET,
            return_value={"run_id": "run_1", "outcome": "failed", "detail": "maximum recursion depth exceeded"},
        ):
            first = generic_repeated_failure_blocks_auto_start(
                "workspace_dashpro", "watcher", now=start, state_path=self.state_path
            )
            still_blocked = generic_repeated_failure_blocks_auto_start(
                "workspace_dashpro",
                "watcher",
                now=start + timedelta(seconds=90),
                state_path=self.state_path,
            )
        self.assertTrue(first)
        self.assertTrue(still_blocked, "same failed run within the 2min first backoff must stay blocked")

    def test_escalating_backoff_on_repeated_failures(self) -> None:
        """Each new failed run_id after cooldown elapses steps to a longer backoff."""
        current = datetime.now(timezone.utc)
        run_index = 1
        expected_windows = [120.0, 300.0, 900.0, 1800.0, 1800.0]  # caps at the last entry

        for expected_seconds in expected_windows:
            run_id = f"run_{run_index}"
            with patch(
                _PATCH_TARGET,
                return_value={"run_id": run_id, "outcome": "failed", "detail": "some unclassified error"},
            ):
                blocked = generic_repeated_failure_blocks_auto_start(
                    "workspace_dashpro", "watcher", now=current, state_path=self.state_path
                )
                self.assertTrue(blocked, f"run {run_id} should block immediately on first failure")

                just_before = generic_repeated_failure_blocks_auto_start(
                    "workspace_dashpro",
                    "watcher",
                    now=current + timedelta(seconds=expected_seconds - 1),
                    state_path=self.state_path,
                )
                self.assertTrue(
                    just_before,
                    f"run {run_id} should still be blocked just before its {expected_seconds}s window elapses",
                )

            current = current + timedelta(seconds=expected_seconds + 1)
            run_index += 1

    def test_success_resets_streak_for_next_failure(self) -> None:
        start = datetime.now(timezone.utc)
        with patch(
            _PATCH_TARGET,
            return_value={"run_id": "run_1", "outcome": "failed", "detail": "some unclassified error"},
        ):
            generic_repeated_failure_blocks_auto_start(
                "workspace_dashpro", "watcher", now=start, state_path=self.state_path
            )
        # Escalate once more so the streak is at least 2.
        with patch(
            _PATCH_TARGET,
            return_value={"run_id": "run_2", "outcome": "failed", "detail": "some unclassified error"},
        ):
            generic_repeated_failure_blocks_auto_start(
                "workspace_dashpro",
                "watcher",
                now=start + timedelta(seconds=121),
                state_path=self.state_path,
            )
        # Now the role succeeds.
        with patch(_PATCH_TARGET, return_value={"run_id": "run_3", "outcome": "completed", "detail": ""}):
            generic_repeated_failure_blocks_auto_start(
                "workspace_dashpro",
                "watcher",
                now=start + timedelta(seconds=500),
                state_path=self.state_path,
            )
        # A brand-new failure afterward should get the *first* (shortest) backoff again.
        later = start + timedelta(seconds=600)
        with patch(
            _PATCH_TARGET,
            return_value={"run_id": "run_4", "outcome": "failed", "detail": "some unclassified error"},
        ):
            generic_repeated_failure_blocks_auto_start(
                "workspace_dashpro", "watcher", now=later, state_path=self.state_path
            )
            open_after_first_window = generic_repeated_failure_blocks_auto_start(
                "workspace_dashpro",
                "watcher",
                now=later + timedelta(seconds=121),
                state_path=self.state_path,
            )
        self.assertFalse(
            open_after_first_window,
            "streak should have reset to the shortest backoff after a success, not stayed escalated",
        )


if __name__ == "__main__":
    unittest.main()
