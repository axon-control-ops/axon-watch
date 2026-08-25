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
    record_completion_gate_receipt,
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
        from app.workspace_agents.verifier_contract import record_acceptance_evidence

        record_acceptance_evidence(
            run_id,
            passed=True,
            summary="targeted checks passed",
            actor="verifier",
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

    def test_report_task_receipt_names_edit_receipt_paths(self) -> None:
        opened = task_store.create_task(
            workspace_id="workspace_dashpro",
            owner_role="lead",
            goal="Document AXON isolation and access acceptance probe findings.",
            acceptance_criteria="Create an ops note if useful and report evidence.",
            allowed_paths=["node_modules", "docs/planning", "docs/ops", "plans"],
        )
        task = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_dashpro-lead",
        )
        run_id = create_run(
            workspace_id="workspace_dashpro",
            mode="agent",
            summary="Lead ops note",
            employee_role="lead",
            task_id=str(task["task_id"]),
            require_leased_task=True,
        )["run_id"]
        self._pass_acceptance(str(run_id))

        with tempfile.TemporaryDirectory() as tempdir:
            result = evaluate_pre_publish_completion_gate(
                run_id=str(run_id),
                task=task,
                isolation_root=Path(tempdir),
                reply_text=(
                    "Created the operator note.\n"
                    ":::edit docs/ops/AXON_FULL_ACCESS_PROBE.md +25 -0\n"
                    ":::\n"
                    "Confidence: 9/10"
                ),
                changed_paths=[],
            )

        self.assertTrue(result.passed, result)
        self.assertEqual(["docs/ops/AXON_FULL_ACCESS_PROBE.md"], result.changed_paths)
        record_completion_gate_receipt(str(run_id), result)
        run = run_store.get_run(str(run_id))
        history = run_store.list_history(str((run or {}).get("history_ref") or ""))
        receipt = next(
            item.get("receipt") for item in history
            if (item.get("receipt") or {}).get("type") == "completion_gate"
        )
        self.assertIn(
            "changed_files=docs/ops/AXON_FULL_ACCESS_PROBE.md",
            str(receipt.get("summary") or ""),
        )

    def _latest_completion_gate_summary(self, run_id: str) -> str:
        run = run_store.get_run(run_id)
        history = run_store.list_history(str((run or {}).get("history_ref") or ""))
        receipt = next(
            item.get("receipt") for item in history
            if (item.get("receipt") or {}).get("type") == "completion_gate"
        )
        return str(receipt.get("summary") or "")

    def test_preflight_receipt_is_labelled_preflight_not_completion(self) -> None:
        """The receipt recorded before publish must not read as the final verdict.

        Regression: a private-material publish block still left an earlier
        ``completion=pass`` receipt in run history from this pre-publish call —
        anyone (agent or operator) reading only that receipt saw a false pass
        for a run that was later failed by the publish gate.
        """
        task = self._leased_backend_task(goal="receipt-backed ops task")
        run_id = self._run_for_task(task)
        result = CompletionGateResult(
            passed=True,
            reason="receipt-backed ops task",
            changed_paths=[],
            expected_files=[],
            validation_status="deferred to delivery receipt",
        )
        record_completion_gate_receipt(run_id, result, final=False)
        summary = self._latest_completion_gate_summary(run_id)
        self.assertTrue(summary.startswith("preflight=pass"), summary)
        self.assertNotIn("completion=", summary)

    def test_post_publish_receipt_is_labelled_completion(self) -> None:
        task = self._leased_backend_task(goal="receipt-backed ops task")
        run_id = self._run_for_task(task)
        result = CompletionGateResult(
            passed=True,
            reason="completion gate passed",
            changed_paths=["supabase/migrations/0001_init.sql"],
            expected_files=["supabase"],
            validation_status="passed",
            commit_sha="abc123",
        )
        record_completion_gate_receipt(run_id, result, final=True)
        summary = self._latest_completion_gate_summary(run_id)
        self.assertTrue(summary.startswith("completion=pass"), summary)

    def test_overlap_note_flags_disjoint_changed_and_expected_files(self) -> None:
        """A receipt-backed pass whose changed files share nothing with the
        task's expected scope is exactly the shape that let a blocked
        private-material delivery (assets/TPS-PACK.zip, ...) sit next to an
        unrelated expected scope (docs/ops, docs/planning, ...) and still
        read as a clean pass."""
        task = self._leased_backend_task(goal="receipt-backed ops task")
        run_id = self._run_for_task(task)
        result = CompletionGateResult(
            passed=True,
            reason="receipt-backed ops task",
            changed_paths=["assets/TPS-PACK.zip", "assets/_extracted/pack/photo.jpeg"],
            expected_files=["node_modules", "docs/planning", "docs/ops", "plans"],
            validation_status="deferred to delivery receipt",
        )
        record_completion_gate_receipt(run_id, result, final=False)
        summary = self._latest_completion_gate_summary(run_id)
        self.assertIn("note=changed_files did not overlap expected_files", summary)

    def test_overlap_note_absent_when_changed_files_are_in_scope(self) -> None:
        task = self._leased_backend_task(goal="receipt-backed ops task")
        run_id = self._run_for_task(task)
        result = CompletionGateResult(
            passed=True,
            reason="receipt-backed ops task",
            changed_paths=["docs/ops/rollup.md"],
            expected_files=["docs/ops", "docs/planning"],
            validation_status="deferred to delivery receipt",
        )
        record_completion_gate_receipt(run_id, result, final=False)
        summary = self._latest_completion_gate_summary(run_id)
        self.assertNotIn("note=", summary)

    def test_overlap_note_absent_on_failed_result(self) -> None:
        """Advisory only on a pass — a failure receipt already says why."""
        task = self._leased_backend_task(goal="receipt-backed ops task")
        run_id = self._run_for_task(task)
        result = CompletionGateResult(
            passed=False,
            reason="Workspace delivery blocked: private_company_material: assets/x.zip",
            changed_paths=["assets/x.zip"],
            expected_files=["docs/ops"],
            validation_status="not checked",
        )
        record_completion_gate_receipt(run_id, result, final=False)
        summary = self._latest_completion_gate_summary(run_id)
        self.assertNotIn("note=", summary)

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

    def test_specialist_verification_handoff_passes_with_terminal_jobs(self) -> None:
        from app.terminal.agent_job_registry import register_job
        from app.workspace_agents.verifier_contract import ensure_acceptance_before_publish

        opened = task_store.create_task(
            workspace_id="workspace_dashpro",
            owner_role="backend",
            goal=(
                "Verification after Marco (backend): run scoped verify commands — "
                "`npm test -- tests/unit/services/staffVisibility.test.ts` "
                "[from run run_demo]"
            ),
            acceptance_criteria="Attach stdout receipts.",
            allowed_paths=[],
        )
        task = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_dashpro-backend",
        )
        run_id = self._run_for_task(task)
        register_job(
            {
                "job_id": "agent-job-verify-gate",
                "workspace_id": "workspace_dashpro",
                "run_id": run_id,
                "command": "npm test -- tests/unit/services/staffVisibility.test.ts",
                "status": "completed",
                "exit_code": 0,
                "created_at": "2026-01-01T00:00:00Z",
            }
        )
        ensure_acceptance_before_publish(run_id, changed_paths=["src/out_of_scope.ts"])

        with tempfile.TemporaryDirectory() as tempdir:
            result = evaluate_pre_publish_completion_gate(
                run_id=run_id,
                task=task,
                isolation_root=Path(tempdir),
                reply_text="Tests passed with terminal stdout attached.",
                changed_paths=["src/out_of_scope.ts"],
            )

        self.assertTrue(result.passed, result)
        self.assertEqual("non-implementation task", result.reason)

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


class ReviewShapedTaskClassificationTests(unittest.TestCase):
    """Regression: a review goal mentioning "fixes" demanded a diff, so an
    honest report failed with "worker produced no changed files"."""

    def _requested(self, goal: str) -> bool:
        from app.workspace_agents.completion_gate import implementation_requested

        return implementation_requested(
            {"owner_role": "backend", "goal": goal, "acceptance_criteria": ""}
        )

    def test_review_then_apply_fixes_is_not_an_implementation_demand(self) -> None:
        self.assertFalse(
            self._requested(
                "Critically review all your previous work for factual errors. "
                "Suggest fixes/improvements - Apply them - Then rewrite the answer."
            )
        )

    def test_audit_goal_is_report_first(self) -> None:
        self.assertFalse(self._requested("Audit the CI workflows and report findings"))

    def test_dashboard_status_report_does_not_match_add_substring(self) -> None:
        self.assertFalse(
            self._requested(
                "Produce a clear status report on the teacher dashboard and "
                "parent/child dashboard flow work completed to date."
            )
        )

    def test_review_that_names_a_build_still_demands_a_diff(self) -> None:
        self.assertTrue(
            self._requested("Review the lessons service and implement the missing endpoint")
        )

    def test_plain_implementation_goals_are_unchanged(self) -> None:
        self.assertTrue(self._requested("Fix the failing lessons service test"))
        self.assertTrue(self._requested("Add a new payments endpoint"))


if __name__ == "__main__":
    unittest.main()
