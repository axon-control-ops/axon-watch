"""Run-outcome edge: restart-cancel with Critical Review success should complete."""

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


class RunOutcomeRestartCriticalReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
    def test_latest_role_outcome_keeps_restart_cancel_when_critical_review_succeeded(self) -> None:
        usage_failed = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Sipho: continuous worker shift",
            employee_role="backend",
        )
        fail_run(
            usage_failed["run_id"],
            receipt_summary=(
                "Lane B agent fallback reply generated (ActionRequiredError: out of usage)"
            ),
        )

        restarted = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Usage limits blocked my last shift on Ops checklists",
            employee_role="backend",
        )
        from app.runs.restart_reconcile import interrupt_run_on_restart

        cancelled = interrupt_run_on_restart(restarted["run_id"])
        assert cancelled is not None
        run_store.append_transition(
            cancelled["history_ref"],
            {
                "receipt": {
                    "type": "critical_review",
                    "summary": (
                        "Critical Review Confidence: 9/10 · intent=lane_b_agent · success=True"
                    ),
                },
            },
        )

        outcome = latest_role_run_outcome("workspace_axon_watch", "backend")
        assert outcome is not None
        self.assertEqual("completed", outcome["outcome"])
        self.assertEqual(restarted["run_id"], outcome["run_id"])
        self.assertIn("Confidence: 9/10", outcome["detail"])


if __name__ == "__main__":
    unittest.main()
