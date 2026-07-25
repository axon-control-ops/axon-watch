"""Gate 4 durable task ledger — create, lease contention, attempt budget."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store, task_store  # noqa: E402


class Gate4TaskLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        self.addCleanup(task_store.reset_store)

    def test_create_and_list_task(self) -> None:
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Fix memory drain in quality-gate heap calc",
            acceptance_criteria="node-heap tests pass",
            owner_role="integrations",
            risk="normal",
            attempt_budget=2,
        )
        self.assertTrue(created["task_id"].startswith("task-"))
        self.assertEqual("open", created["status"])
        self.assertEqual(0, created["attempts_used"])
        self.assertEqual(2, created["attempt_budget"])

        listed = task_store.list_tasks(
            workspace_id="workspace_dashpro",
            owner_role="integrations",
        )
        self.assertEqual(1, len(listed))
        self.assertEqual(created["task_id"], listed[0]["task_id"])

    def test_lease_contention_only_one_winner(self) -> None:
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Lease contention proof",
            owner_role="backend",
        )
        first = task_store.lease_task(
            created["task_id"],
            lease_holder="employee-workspace_dashpro-backend-1",
            run_id="run_first",
        )
        self.assertEqual("leased", first["status"])
        self.assertEqual(1, first["attempts_used"])
        self.assertEqual("employee-workspace_dashpro-backend-1", first["lease_holder"])

        with self.assertRaises(task_store.TaskLedgerError) as ctx:
            task_store.lease_task(
                created["task_id"],
                lease_holder="employee-workspace_dashpro-backend-2",
            )
        self.assertIn("already leased", str(ctx.exception).lower())

        still = task_store.get_task(created["task_id"])
        assert still is not None
        self.assertEqual("employee-workspace_dashpro-backend-1", still["lease_holder"])

    def test_attempt_budget_blocks_release_after_exhaustion(self) -> None:
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Budget proof",
            owner_role="frontend",
            attempt_budget=1,
        )
        leased = task_store.lease_task(
            created["task_id"],
            lease_holder="employee-workspace_dashpro-frontend-2",
        )
        failed = task_store.fail_task(
            leased["task_id"],
            terminal_outcome="tooling failed",
            reopen_if_budget_remaining=True,
        )
        # Budget was 1 and attempts_used is 1 — fail finalizes instead of reopening.
        self.assertEqual("failed", failed["status"])
        self.assertEqual(1, failed["attempts_used"])

        with self.assertRaises(task_store.TaskLedgerError) as ctx:
            task_store.lease_task(
                created["task_id"],
                lease_holder="employee-workspace_dashpro-frontend-2",
            )
        self.assertTrue(
            "terminal" in str(ctx.exception).lower()
            or "attempt budget" in str(ctx.exception).lower()
        )

    def test_fail_reopens_when_budget_remaining(self) -> None:
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Retryable task",
            owner_role="integrations",
            attempt_budget=3,
        )
        task_store.lease_task(created["task_id"], lease_holder="soren")
        reopened = task_store.fail_task(
            created["task_id"],
            terminal_outcome="transient",
            reopen_if_budget_remaining=True,
        )
        self.assertEqual("open", reopened["status"])
        self.assertIsNone(reopened["lease_holder"])
        self.assertEqual(1, reopened["attempts_used"])

        again = task_store.lease_task(created["task_id"], lease_holder="soren")
        self.assertEqual("leased", again["status"])
        self.assertEqual(2, again["attempts_used"])

    def test_complete_task_is_terminal(self) -> None:
        created = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Ship fix",
            owner_role="backend",
        )
        task_store.lease_task(created["task_id"], lease_holder="marco", run_id="run_ok")
        done = task_store.complete_task(
            created["task_id"],
            terminal_outcome="acceptance met",
            run_id="run_ok",
        )
        self.assertEqual("completed", done["status"])
        self.assertEqual("acceptance met", done["terminal_outcome"])
        with self.assertRaises(task_store.TaskLedgerError):
            task_store.lease_task(created["task_id"], lease_holder="marco")

    def test_claim_open_task_for_role_leases_oldest(self) -> None:
        first = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Oldest goal",
            owner_role="backend",
        )
        task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Newer goal",
            owner_role="backend",
        )
        claimed = task_store.claim_open_task_for_role(
            workspace_id="workspace_dashpro",
            owner_role="backend",
            lease_holder="employee-workspace_dashpro-backend",
        )
        assert claimed is not None
        self.assertEqual(first["task_id"], claimed["task_id"])
        self.assertEqual("leased", claimed["status"])
        self.assertIsNone(
            task_store.claim_open_task_for_role(
                workspace_id="workspace_dashpro",
                owner_role="frontend",
                lease_holder="employee-workspace_dashpro-frontend",
            )
        )

    def test_create_run_require_leased_task_refuses_without_task_id(self) -> None:
        from app.runs.service import RunLifecycleError, create_run

        with self.assertRaises(RunLifecycleError):
            create_run(
                workspace_id="workspace_dashpro",
                mode="agent",
                summary="missing task",
                employee_role="backend",
                require_leased_task=True,
            )

        opened = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Wire create_run to lease",
            owner_role="backend",
        )
        leased = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_dashpro-backend",
        )
        created = create_run(
            workspace_id="workspace_dashpro",
            mode="agent",
            summary="leased worker shift",
            employee_role="backend",
            task_id=leased["task_id"],
            require_leased_task=True,
        )
        self.assertEqual(leased["task_id"], created.get("task_id"))
        bound = task_store.get_task(leased["task_id"])
        assert bound is not None
        self.assertEqual(created["run_id"], bound.get("run_id"))

    def test_dependency_blocks_lease_until_completed(self) -> None:
        parent = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Parent work",
            owner_role="backend",
        )
        child = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Child work",
            owner_role="backend",
            dependencies=[parent["task_id"]],
        )
        with self.assertRaises(task_store.TaskLedgerError) as ctx:
            task_store.lease_task(
                child["task_id"],
                lease_holder="employee-workspace_dashpro-backend",
            )
        self.assertIn("dependency", str(ctx.exception).lower())

        leased_parent = task_store.lease_task(
            parent["task_id"],
            lease_holder="employee-workspace_dashpro-backend",
        )
        task_store.complete_task(leased_parent["task_id"])
        leased_child = task_store.lease_task(
            child["task_id"],
            lease_holder="employee-workspace_dashpro-backend",
        )
        self.assertEqual("leased", leased_child["status"])

    def test_renew_lease_extends_expiry(self) -> None:
        opened = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Long shift",
            owner_role="integrations",
        )
        leased = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_dashpro-integrations",
            lease_seconds=60,
        )
        before = leased.get("lease_expires_at")
        renewed = task_store.renew_lease(
            opened["task_id"],
            lease_holder="employee-workspace_dashpro-integrations",
            lease_seconds=3600,
        )
        self.assertEqual("leased", renewed["status"])
        self.assertNotEqual(before, renewed.get("lease_expires_at"))


if __name__ == "__main__":
    unittest.main()
