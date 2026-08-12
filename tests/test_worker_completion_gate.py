from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store, task_store  # noqa: E402
from app.runs.service import append_run_execution_receipt, create_run  # noqa: E402
from app.workspace_agents.completion_gate import (  # noqa: E402
    CompletionGateResult,
    evaluate_post_publish_completion_gate,
    evaluate_pre_publish_completion_gate,
)


class WorkerCompletionGateTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        self.addCleanup(task_store.reset_store)

    def _leased_frontend_task(self, *, goal: str, acceptance: str = "") -> dict:
        opened = task_store.create_task(
            workspace_id="workspace_dashpro",
            owner_role="frontend",
            goal=goal,
            acceptance_criteria=acceptance,
            allowed_paths=["app", "components", "features", "screens", "hooks"],
        )
        return task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_dashpro-frontend",
        )

    def _leased_backend_task(self, *, goal: str, acceptance: str = "") -> dict:
        opened = task_store.create_task(
            workspace_id="workspace_dashpro",
            owner_role="backend",
            goal=goal,
            acceptance_criteria=acceptance,
            allowed_paths=["supabase", "scripts", "tests"],
        )
        return task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_dashpro-backend",
        )

    def _run_for_task(self, task: dict) -> str:
        run = create_run(
            workspace_id=str(task["workspace_id"]),
            mode="agent",
            summary=f"{task['owner_role']} worker",
            employee_role=str(task["owner_role"]),
            task_id=str(task["task_id"]),
            require_leased_task=True,
        )
        return str(run["run_id"])

    def _pass_acceptance(self, run_id: str, *, with_checks: bool = False) -> None:
        append_run_execution_receipt(
            run_id,
            receipt_type="acceptance_evidence",
            receipt_summary="acceptance=pass · targeted checks passed",
            actor="verifier",
            success=True,
            intent="gate6_acceptance",
        )
        if with_checks:
            append_run_execution_receipt(
                run_id,
                receipt_type="acceptance_check_outputs",
                receipt_summary="checks=targeted-test count=1 passed=True",
                actor="verifier",
                success=True,
                intent="gate6_check_outputs",
            )

    def test_stale_no_change_implementation_is_rejected(self) -> None:
        task = self._leased_frontend_task(goal="Redesign the Student Management header UI.")
        run_id = self._run_for_task(task)
        self._pass_acceptance(run_id)

        with tempfile.TemporaryDirectory() as tempdir:
            result = evaluate_pre_publish_completion_gate(
                run_id=run_id,
                task=task,
                isolation_root=Path(tempdir),
                reply_text="Continued after the server restart. No files changed.",
                changed_paths=[],
            )

        self.assertFalse(result.passed)
        self.assertIn("no changed files", result.reason)

    def test_watcher_report_does_not_require_a_product_diff(self) -> None:
        opened = task_store.create_task(
            workspace_id="workspace_dashpro",
            owner_role="watcher",
            goal="Verify the dashboard fix and report any remaining issue.",
            acceptance_criteria="Check the flow and report results.",
            allowed_paths=[],
        )
        task = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_dashpro-watcher",
        )
        run_id = create_run(
            workspace_id="workspace_dashpro",
            mode="agent",
            summary="Watcher verification",
            employee_role="watcher",
            task_id=str(task["task_id"]),
            require_leased_task=True,
        )["run_id"]
        self._pass_acceptance(str(run_id), with_checks=True)

        with tempfile.TemporaryDirectory() as tempdir:
            result = evaluate_pre_publish_completion_gate(
                run_id=str(run_id),
                task=task,
                isolation_root=Path(tempdir),
                reply_text="Verified the dashboard flow and recorded the results.",
                changed_paths=[],
            )

        self.assertTrue(result.passed, result)
        self.assertEqual("non-implementation task", result.reason)

    def test_integrations_verification_report_does_not_require_a_product_diff(self) -> None:
        opened = task_store.create_task(
            workspace_id="workspace_dashpro",
            owner_role="integrations",
            goal="Verify workflow files and self-hosted runner health; report blockers.",
            acceptance_criteria="Report workflow evidence and runner health status.",
            allowed_paths=[".github", "config", "scripts"],
        )
        task = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_dashpro-integrations",
        )
        run_id = create_run(
            workspace_id="workspace_dashpro",
            mode="agent",
            summary="Integrations verification",
            employee_role="integrations",
            task_id=str(task["task_id"]),
            require_leased_task=True,
        )["run_id"]
        self._pass_acceptance(str(run_id), with_checks=True)

        with tempfile.TemporaryDirectory() as tempdir:
            result = evaluate_pre_publish_completion_gate(
                run_id=str(run_id),
                task=task,
                isolation_root=Path(tempdir),
                reply_text=(
                    "Changed files: none. Verified workflow files and reported "
                    "that live runner health remains blocked."
                ),
                changed_paths=[],
            )

        self.assertTrue(result.passed, result)
        self.assertEqual("non-implementation task", result.reason)

    def test_verification_refusal_without_command_receipts_cannot_pass(self) -> None:
        opened = task_store.create_task(
            workspace_id="workspace_dashpro",
            owner_role="watcher",
            goal="Review the working tree and verify runtime health before delivery.",
            acceptance_criteria="Report verified command results.",
            allowed_paths=[],
        )
        task = task_store.lease_task(
            opened["task_id"], lease_holder="employee-workspace_dashpro-watcher"
        )
        run_id = create_run(
            workspace_id="workspace_dashpro", mode="agent", summary="Release review",
            employee_role="watcher", task_id=str(task["task_id"]), require_leased_task=True,
        )["run_id"]

        with tempfile.TemporaryDirectory() as tempdir:
            result = evaluate_pre_publish_completion_gate(
                run_id=str(run_id), task=task, isolation_root=Path(tempdir),
                reply_text="I cannot complete the gate; command receipts are missing.",
                changed_paths=[],
            )

        self.assertFalse(result.passed)
        self.assertIn("required evidence", result.reason)

    def test_integrations_fix_still_requires_a_product_diff(self) -> None:
        opened = task_store.create_task(
            workspace_id="workspace_dashpro",
            owner_role="integrations",
            goal="Fix GitHub Actions npm cache wiring.",
            acceptance_criteria="Validation command passes.",
            allowed_paths=[".github", "config", "scripts"],
        )
        task = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_dashpro-integrations",
        )
        run_id = create_run(
            workspace_id="workspace_dashpro",
            mode="agent",
            summary="Integrations fix",
            employee_role="integrations",
            task_id=str(task["task_id"]),
            require_leased_task=True,
        )["run_id"]
        self._pass_acceptance(str(run_id), with_checks=True)

        with tempfile.TemporaryDirectory() as tempdir:
            result = evaluate_pre_publish_completion_gate(
                run_id=str(run_id),
                task=task,
                isolation_root=Path(tempdir),
                reply_text="Changed files: none. No integrations change was required.",
                changed_paths=[],
            )

        self.assertFalse(result.passed)
        self.assertIn("no changed files", result.reason)

    def test_wrong_objective_diff_is_rejected(self) -> None:
        task = self._leased_frontend_task(goal="Redesign the Student Management header UI.")
        run_id = self._run_for_task(task)
        self._pass_acceptance(run_id)

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            path = root / "app" / "PracticePoemScreen.tsx"
            path.parent.mkdir(parents=True)
            path.write_text("export const PracticePoemScreen = () => null\n", encoding="utf-8")
            result = evaluate_pre_publish_completion_gate(
                run_id=run_id,
                task=task,
                isolation_root=root,
                reply_text="Changed files: app/PracticePoemScreen.tsx",
                changed_paths=["app/PracticePoemScreen.tsx"],
            )

        self.assertFalse(result.passed)
        self.assertIn("do not map", result.reason)

    def test_matching_diff_validation_and_commit_is_accepted(self) -> None:
        task = self._leased_frontend_task(
            goal="Redesign the Student Management header UI.",
            acceptance="Run targeted validation command and report results.",
        )
        run_id = self._run_for_task(task)
        self._pass_acceptance(run_id, with_checks=True)

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            path = root / "app" / "StudentManagementScreen.tsx"
            path.parent.mkdir(parents=True)
            path.write_text("export const StudentManagementScreen = () => null\n", encoding="utf-8")
            preflight = evaluate_pre_publish_completion_gate(
                run_id=run_id,
                task=task,
                isolation_root=root,
                reply_text="Changed files: app/StudentManagementScreen.tsx. Validation passed.",
                changed_paths=["app/StudentManagementScreen.tsx"],
            )

        self.assertTrue(preflight.passed, preflight)
        final = evaluate_post_publish_completion_gate(
            task=task,
            delivery={"commit_sha": "abc123def456", "refs": {}},
            preflight=preflight,
        )
        self.assertTrue(final.passed, final)
        self.assertEqual("abc123def456", final.commit_sha)

    def test_code_change_without_commit_hash_is_rejected_after_publish(self) -> None:
        preflight = CompletionGateResult(
            passed=True,
            reason="completion gate passed",
            changed_paths=["app/StudentManagementScreen.tsx"],
            expected_files=["app"],
            validation_status="passed",
        )
        task = self._leased_frontend_task(goal="Fix Student Management UI.")

        result = evaluate_post_publish_completion_gate(
            task=task,
            delivery={"refs": {}},
            preflight=preflight,
        )

        self.assertFalse(result.passed)
        self.assertIn("no commit hash", result.reason)

    def test_backend_migration_fix_requires_validation_outputs(self) -> None:
        task = self._leased_backend_task(
            goal="Fix the Supabase migration SQL lint failure.",
            acceptance="Run SQLFluff lint on the changed migration and report the command output.",
        )
        run_id = self._run_for_task(task)
        self._pass_acceptance(run_id, with_checks=False)

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            path = root / "supabase" / "migrations" / "20260811130000_practice.sql"
            path.parent.mkdir(parents=True)
            path.write_text("select 1;\n", encoding="utf-8")
            result = evaluate_pre_publish_completion_gate(
                run_id=run_id,
                task=task,
                isolation_root=root,
                reply_text=(
                    "Changed files: supabase/migrations/20260811130000_practice.sql. "
                    "SQL lint fixed."
                ),
                changed_paths=["supabase/migrations/20260811130000_practice.sql"],
            )

        self.assertFalse(result.passed)
        self.assertIn("missing validation command outputs", result.reason)


if __name__ == "__main__":
    unittest.main()
