"""Orphaned run reconciliation after control-plane restart."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store  # noqa: E402
from app.runs.service import (  # noqa: E402
    create_run,
    get_run,
    mark_review_ready,
    reconcile_orphaned_runs_on_startup,
)
from tests.support.control_plane_db import isolate_control_plane_db  # noqa: E402


class RunStartupReconcileTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_reconcile_fails_executing_runs_left_by_prior_process(self) -> None:
        record = create_run(
            workspace_id="workspace_axon_watch",
            mode="debug",
            summary="Debug voice",
            detail="Lane B debug-mode evidence loop",
            requires_approval=False,
        )
        run_id = str(record["run_id"])
        self.assertEqual(get_run(run_id)["phase"], "executing")

        reconciled = reconcile_orphaned_runs_on_startup(boot_id="boot-test")

        self.assertEqual(reconciled, [run_id])
        self.assertEqual(get_run(run_id)["phase"], "failed")

    def test_reconcile_leaves_review_ready_runs_alone(self) -> None:
        record = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Review me",
            detail="Lane B agent-mode runtime request",
            requires_approval=False,
        )
        run_id = str(record["run_id"])
        mark_review_ready(run_id)

        reconciled = reconcile_orphaned_runs_on_startup(boot_id="boot-test")

        self.assertEqual(reconciled, [])
        self.assertEqual(get_run(run_id)["phase"], "review_ready")


if __name__ == "__main__":
    unittest.main()
