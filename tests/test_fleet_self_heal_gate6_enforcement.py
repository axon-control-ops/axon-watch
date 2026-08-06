"""Black-box proof: VAXON fleet-repair runs get Gate 6 + Critical Review for free.

Pins that a task-bound fleet self-heal run cannot reach review_ready/complete
without a passing acceptance_evidence receipt — a regression guard so a
future refactor of verifier_contract.py can't silently exempt VAXON runs from
the same rigor every other leased worker task already gets.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store, task_store  # noqa: E402
from app.runs.acceptance_transitions import mark_review_ready  # noqa: E402
from app.runs.service import RunLifecycleError, complete_run, create_run  # noqa: E402
from app.workspace_agents.verifier_contract import record_acceptance_evidence  # noqa: E402


class FleetRepairGate6EnforcementTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        db_path = str(Path(self._tmpdir.name) / "cp.sqlite3")
        os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = db_path
        self.addCleanup(lambda: os.environ.pop("AXON_WATCH_CONTROL_PLANE_DB", None))
        task_store.reset_store()
        run_store.reset_store()
        self.addCleanup(task_store.reset_store)
        self.addCleanup(run_store.reset_store)

    def _leased_fleet_repair_run(self) -> dict:
        opened = task_store.create_task(
            workspace_id="workspace_axon_watch",
            goal="VAXON fleet repair [fleetbug:sandbox_resolution:abc123]: sandbox failures.",
            acceptance_criteria="root-cause it, add a regression test, confirm green Fast Gate.",
            owner_role="watcher",
            attempt_budget=3,
        )
        task_store.lease_task(str(opened["task_id"]), lease_holder="vaxon-fleet-repair-abc123")
        return create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Rowan: VAXON fleet repair fleetbug:sandbox_resolution:abc123",
            employee_role="watcher",
            task_id=str(opened["task_id"]),
            require_leased_task=True,
        )

    def test_complete_run_blocked_without_acceptance_evidence(self) -> None:
        run = self._leased_fleet_repair_run()
        with self.assertRaises(RunLifecycleError) as ctx:
            complete_run(str(run["run_id"]))
        self.assertIn("Gate 6", str(ctx.exception))

    def test_mark_review_ready_blocked_without_acceptance_evidence(self) -> None:
        run = self._leased_fleet_repair_run()
        with self.assertRaises(RunLifecycleError) as ctx:
            mark_review_ready(str(run["run_id"]))
        self.assertIn("Gate 6", str(ctx.exception))

    def test_complete_run_succeeds_once_a_passing_acceptance_receipt_exists(self) -> None:
        run = self._leased_fleet_repair_run()
        record_acceptance_evidence(
            str(run["run_id"]), passed=True, summary="tests pass, regression covered",
        )
        completed = complete_run(str(run["run_id"]))
        self.assertEqual("completed", completed["phase"])

    def test_complete_run_still_blocked_after_a_failing_acceptance_receipt(self) -> None:
        run = self._leased_fleet_repair_run()
        record_acceptance_evidence(
            str(run["run_id"]), passed=False, summary="regression test still failing",
        )
        with self.assertRaises(RunLifecycleError) as ctx:
            complete_run(str(run["run_id"]))
        self.assertIn("Gate 6", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
