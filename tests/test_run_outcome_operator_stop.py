"""Run-outcome edge: operator-stopped CLI runs should not eclipse real failures."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store  # noqa: E402
from app.runs.service import create_run, fail_run  # noqa: E402
from app.workspace_agents.run_outcome import latest_role_run_outcome  # noqa: E402


class RunOutcomeOperatorStopTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_latest_role_outcome_skips_operator_stopped_interruptions(self) -> None:
        real_failure = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Reed: backend shift",
            employee_role="backend",
        )
        fail_run(
            real_failure["run_id"],
            receipt_summary="verify:contracts — test_run_outcome.py: assertion failed",
        )

        stopped = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Reed: continuous worker shift",
            employee_role="backend",
        )
        fail_run(
            stopped["run_id"],
            receipt_summary=(
                "Lane B agent fallback reply generated "
                "(Runtime execution stopped by operator before the CLI finished.)"
            ),
        )

        outcome = latest_role_run_outcome("workspace_axon_watch", "backend")
        assert outcome is not None
        self.assertEqual("failed", outcome["outcome"])
        self.assertIn("assertion failed", outcome["detail"])
        self.assertEqual(real_failure["run_id"], outcome["run_id"])

    def test_latest_role_outcome_omits_operator_stopped_only_failure(self) -> None:
        stopped = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Reed: continuous worker shift",
            employee_role="backend",
        )
        fail_run(
            stopped["run_id"],
            receipt_summary=(
                "Lane B agent fallback reply generated "
                "(Runtime execution stopped by operator before the CLI finished.)"
            ),
        )

        self.assertIsNone(latest_role_run_outcome("workspace_axon_watch", "backend"))


if __name__ == "__main__":
    unittest.main()
