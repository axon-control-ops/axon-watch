"""Run-outcome edge: stale timeout with Critical Review success should complete."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store  # noqa: E402
from app.runs.service import create_run, fail_run  # noqa: E402
from app.workspace_agents.failure_detail import is_stale_timeout_failure  # noqa: E402
from app.workspace_agents.run_outcome import latest_role_run_outcome  # noqa: E402


class RunOutcomeStaleCriticalReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_is_stale_timeout_failure_markers(self) -> None:
        self.assertTrue(
            is_stale_timeout_failure(
                "Continuous worker run exceeded stale timeout (929s > 720s)"
            )
        )
        self.assertFalse(
            is_stale_timeout_failure(
                "Lane B agent reply generated via Cursor CLI (local) · success=True"
            )
        )

    def test_latest_role_outcome_completes_stale_fail_when_critical_review_succeeded(
        self,
    ) -> None:
        created = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Rowan: CI repair Axon-X Fast Gate",
            employee_role="watcher",
        )
        fail_run(
            created["run_id"],
            receipt_summary="Continuous worker run exceeded stale timeout (929s > 720s)",
            actor="workspace_scheduler",
        )
        # Late finalize after the stale reap (matches run_d3002d9522af receipts).
        run_store.append_transition(
            created["history_ref"],
            {
                "receipt": {
                    "type": "runtime_dispatch",
                    "summary": (
                        "Lane B agent reply generated via Cursor CLI (local) "
                        "· intent=lane_b_agent · success=True"
                    ),
                },
            },
        )
        run_store.append_transition(
            created["history_ref"],
            {
                "receipt": {
                    "type": "critical_review",
                    "summary": (
                        "Critical Review Confidence: 9/10 · intent=lane_b_agent · success=True"
                    ),
                },
            },
        )

        outcome = latest_role_run_outcome("workspace_axon_watch", "watcher")
        assert outcome is not None
        self.assertEqual("completed", outcome["outcome"])
        self.assertEqual(created["run_id"], outcome["run_id"])
        self.assertIn("Confidence: 9/10", outcome["detail"])

    def test_failure_detail_prefers_stale_run_failed_over_success_dispatch(self) -> None:
        created = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Rowan: CI repair Axon-X Fast Gate",
            employee_role="watcher",
        )
        fail_run(
            created["run_id"],
            receipt_summary="Continuous worker run exceeded stale timeout (929s > 720s)",
            actor="workspace_scheduler",
        )
        run_store.append_transition(
            created["history_ref"],
            {
                "receipt": {
                    "type": "runtime_dispatch",
                    "summary": (
                        "Lane B agent reply generated via Cursor CLI (local) "
                        "· intent=lane_b_agent · success=True"
                    ),
                },
            },
        )
        # No Critical Review — still a real failure, but detail must not be success=True.
        outcome = latest_role_run_outcome("workspace_axon_watch", "watcher")
        assert outcome is not None
        self.assertEqual("failed", outcome["outcome"])
        self.assertIn("stale timeout", outcome["detail"].lower())
        self.assertNotIn("success=True", outcome["detail"])


if __name__ == "__main__":
    unittest.main()
