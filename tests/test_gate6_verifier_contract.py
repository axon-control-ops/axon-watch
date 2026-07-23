"""Gate 6 verifier contract — fail-closed acceptance evidence for leased worker runs."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store, task_store  # noqa: E402
from app.runs.service import (  # noqa: E402
    RunLifecycleError,
    complete_run,
    create_run,
    mark_review_ready,
)
from app.workspace_agents.verifier_contract import (  # noqa: E402
    has_passing_acceptance_evidence,
    record_acceptance_evidence,
)


class Gate6VerifierContractTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        self.addCleanup(task_store.reset_store)

    def _leased_executing_run(self) -> dict:
        task = task_store.create_task(
            workspace_id="workspace_axon_watch",
            goal="Gate 6 acceptance",
            acceptance_criteria="tests pass",
            owner_role="implementer",
        )
        leased = task_store.lease_task(
            str(task["task_id"]),
            lease_holder="implementer",
        )
        return create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Leased worker run",
            employee_role="implementer",
            task_id=str(leased["task_id"]),
        )

    def test_review_ready_blocked_without_acceptance_for_task_run(self) -> None:
        created = self._leased_executing_run()
        self.assertTrue(str(created.get("task_id") or ""))
        with self.assertRaises(RunLifecycleError) as ctx:
            mark_review_ready(str(created["run_id"]))
        self.assertIn("acceptance_evidence", str(ctx.exception))

    def test_review_ready_blocked_when_acceptance_failed(self) -> None:
        created = self._leased_executing_run()
        record_acceptance_evidence(
            str(created["run_id"]),
            passed=False,
            summary="unit tests failed",
        )
        self.assertFalse(has_passing_acceptance_evidence(str(created["run_id"])))
        with self.assertRaises(RunLifecycleError) as ctx:
            mark_review_ready(str(created["run_id"]))
        self.assertIn("did not pass", str(ctx.exception))

    def test_review_ready_allowed_with_passing_acceptance(self) -> None:
        created = self._leased_executing_run()
        record_acceptance_evidence(
            str(created["run_id"]),
            passed=True,
            summary="lint+unit pass",
        )
        reviewed = mark_review_ready(str(created["run_id"]))
        self.assertEqual("review_ready", reviewed["phase"])

    def test_complete_from_executing_blocked_without_acceptance_for_task_run(self) -> None:
        created = self._leased_executing_run()
        with self.assertRaises(RunLifecycleError) as ctx:
            complete_run(str(created["run_id"]))
        self.assertIn("acceptance_evidence", str(ctx.exception))

    def test_operator_run_without_task_id_still_reaches_review_ready(self) -> None:
        created = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Operator thin slice",
        )
        reviewed = mark_review_ready(str(created["run_id"]))
        self.assertEqual("review_ready", reviewed["phase"])


if __name__ == "__main__":
    unittest.main()
