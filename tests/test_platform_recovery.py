"""Classifier, policy, retry, checkpoint, and dispatch recovery contracts."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from tests.support.control_plane_app_loader import prepare_control_plane_imports
from tests.support.control_plane_db import isolate_control_plane_db


class FailureClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = prepare_control_plane_imports()
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        import sys as sys_mod

        from tests.support.control_plane_app_loader import CONTROL_PLANE_ROOT as root

        for name in list(sys_mod.modules):
            if name == "app" or name.startswith("app."):
                sys_mod.modules.pop(name, None)
        sys_mod.modules.update(self._saved)
        _ = root

    def test_auth_failure_is_not_retryable(self) -> None:
        from app.platform_recovery.classifier import classify_failure_class
        from app.platform_recovery.policy import policy_for

        failure = classify_failure_class(detail="401 unauthorized invalid api key")
        self.assertEqual("PROVIDER_AUTH_FAILURE", failure)
        policy = policy_for(failure)
        self.assertEqual(0, policy.max_attempts)
        self.assertEqual("FIX_CREDENTIALS", policy.action)

    def test_unknown_does_not_guess_a_retry(self) -> None:
        from app.platform_recovery.classifier import classify_failure_class
        from app.platform_recovery.policy import policy_for

        failure = classify_failure_class(detail="something odd happened")
        self.assertEqual("UNKNOWN", failure)
        self.assertEqual("HUMAN_REVIEW", policy_for(failure).action)

    def test_current_missing_task_failure_is_not_overridden_by_old_timeout(self) -> None:
        from app.platform_recovery.classifier import classify_run_record

        failure = classify_run_record(
            {"current_step": "Continuous worker dispatch cancelled: linked task is missing"},
            history=[
                {
                    "receipt": {
                        "type": "worker_failed",
                        "summary": "An earlier provider call timed out",
                    }
                }
            ],
        )
        self.assertEqual("CONFIGURATION_FAILURE", failure)

    def test_private_material_gate_is_not_classified_as_provider_timeout(self) -> None:
        from app.platform_recovery.classifier import classify_run_record

        failure = classify_run_record(
            {
                "current_step": (
                    "Workspace delivery blocked at blocked: private_company_material: "
                    "assets/TPS-PACK.zip must stay local/private"
                )
            },
            history=[{"receipt": {"summary": "An earlier provider call timed out"}}],
        )
        self.assertEqual("VERIFIER_FAILURE", failure)

    def test_operator_stop_is_never_recast_as_safe_provider_retry(self) -> None:
        from app.platform_recovery.classifier import classify_run_record

        failure = classify_run_record(
            {"current_step": "Run cancelled by operator stop"},
            history=[{"receipt": {"summary": "An earlier provider call timed out"}}],
        )
        self.assertEqual("UNKNOWN", failure)

    def test_no_change_completion_failure_requires_inspection(self) -> None:
        from app.platform_recovery.classifier import classify_run_record

        failure = classify_run_record(
            {
                "current_step": (
                    "Workspace delivery blocked by completion gate: implementation requested "
                    "but worker produced no changed files"
                )
            },
            history=[{"receipt": {"summary": "An earlier provider call timed out"}}],
        )
        self.assertEqual("VERIFIER_FAILURE", failure)

    def test_recovery_attention_keeps_latest_terminal_per_agent(self) -> None:
        from app.platform_recovery.projection import _select_actionable_records

        now = datetime.now(timezone.utc)
        recent = (now - timedelta(minutes=5)).isoformat()
        older = (now - timedelta(hours=2)).isoformat()
        expired = (now - timedelta(days=2)).isoformat()
        selected = _select_actionable_records(
            [
                {
                    "run_id": "old",
                    "workspace_id": "workspace_tps",
                    "employee_role": "lead",
                    "phase": "failed",
                    "ended_at": older,
                },
                {
                    "run_id": "latest",
                    "workspace_id": "workspace_tps",
                    "employee_role": "lead",
                    "phase": "failed",
                    "ended_at": recent,
                },
                {
                    "run_id": "expired",
                    "workspace_id": "workspace_other",
                    "employee_role": "lead",
                    "phase": "failed",
                    "ended_at": expired,
                },
            ],
            now=now,
        )
        self.assertEqual(["latest"], [item["run_id"] for item in selected])

    def test_active_agent_supersedes_its_terminal_attention(self) -> None:
        from app.platform_recovery.projection import _select_actionable_records

        now = datetime.now(timezone.utc)
        selected = _select_actionable_records(
            [
                {
                    "run_id": "failed",
                    "workspace_id": "workspace_tps",
                    "employee_role": "lead",
                    "phase": "failed",
                    "ended_at": now.isoformat(),
                },
                {
                    "run_id": "active",
                    "workspace_id": "workspace_tps",
                    "employee_role": "lead",
                    "phase": "executing",
                    "updated_at": now.isoformat(),
                },
            ],
            now=now,
        )
        self.assertEqual(["active"], [item["run_id"] for item in selected])

    def test_timeout_uses_bounded_backoff(self) -> None:
        from app.platform_recovery.classifier import classify_failure_class
        from app.platform_recovery.policy import policy_for

        policy = policy_for(classify_failure_class(detail="provider timed out"))
        self.assertEqual("PROVIDER_TIMEOUT", policy.failure_class)
        self.assertGreaterEqual(policy.max_attempts, 2)
        self.assertTrue(policy.backoff_seconds)

    def test_retry_fingerprint_escalates_to_human_review(self) -> None:
        from app.platform_recovery.retry_fingerprint import (
            build_retry_fingerprint,
            decide_retry,
        )

        fingerprint = build_retry_fingerprint(
            failure_class="PROVIDER_TIMEOUT",
            provider="cursor",
            task_id="task_1",
            error_signature="timed out",
        )
        fourth = decide_retry(fingerprint=fingerprint, prior_attempts=3, max_attempts=3)
        self.assertEqual("HUMAN_REVIEW", fourth.action)

    def test_redacts_secrets_from_error_text(self) -> None:
        from app.platform_recovery.classifier import redact_secrets

        redacted = redact_secrets("api_key=sk-secret-value token=abc")
        self.assertNotIn("sk-secret-value", redacted)
        self.assertIn("<redacted>", redacted)


class CheckpointAndDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = prepare_control_plane_imports()
        self.addCleanup(self._restore)
        from app.persistence import run_store, task_store
        from app.platform_recovery.store import reset_store

        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        reset_store()
        self.addCleanup(task_store.reset_store)
        self.addCleanup(reset_store)

    def _restore(self) -> None:
        import sys as sys_mod

        for name in list(sys_mod.modules):
            if name == "app" or name.startswith("app."):
                sys_mod.modules.pop(name, None)
        sys_mod.modules.update(self._saved)

    def test_checkpoint_round_trip_omits_blank_run(self) -> None:
        from app.platform_recovery.checkpoints import (
            checkpoint_is_valid,
            get_checkpoint,
            write_checkpoint,
        )

        record = write_checkpoint(
            "run_abc",
            {
                "task_id": "task_1",
                "workspace_id": "workspace_tps",
                "current_stage": "executing",
                "execution_provider": "cursor",
                "changed_paths": ["README.md"],
                "token": "should-not-store",
            },
        )
        self.assertEqual("run_abc", record["run_id"])
        self.assertEqual(["README.md"], record["changed_paths"])
        self.assertTrue(checkpoint_is_valid(get_checkpoint("run_abc")))
        self.assertNotIn("token", record)

    def test_duplicate_dispatch_blocked_for_live_leased_task(self) -> None:
        from app.persistence import task_store
        from app.platform_recovery.dispatch_guard import (
            DuplicateDispatchError,
            assert_dispatch_allowed,
        )
        from app.runs.service import create_run

        opened = task_store.create_task(
            workspace_id="workspace_tps",
            goal="Ship site",
            owner_role="lead",
        )
        leased = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_tps-lead",
        )
        first = create_run(
            workspace_id="workspace_tps",
            mode="agent",
            summary="Lead shift",
            employee_role="lead",
            task_id=leased["task_id"],
            require_leased_task=True,
        )
        with self.assertRaises(DuplicateDispatchError):
            assert_dispatch_allowed(
                task_id=str(leased["task_id"]),
                run_id="run_other",
                active_task_ids={str(leased["task_id"]): str(first["run_id"])},
            )

    def test_acknowledge_clears_attention_without_changing_run_phase(self) -> None:
        from app.platform_recovery.projection import build_recovery_center
        from app.platform_recovery.store import acknowledge_recovery
        from app.runs.service import create_run, fail_run, get_run

        run = create_run(
            workspace_id="workspace_tps",
            mode="agent",
            summary="Inspect failed delivery",
        )
        fail_run(str(run["run_id"]), receipt_summary="Delivery failed")
        before = build_recovery_center(workspace_id="workspace_tps")
        self.assertEqual(1, before["attention_count"])
        item = before["items"][0]
        self.assertTrue(item["actionable"])
        recovery_id = str(item["recovery_id"])

        acknowledged = acknowledge_recovery(recovery_id)
        self.assertIsNotNone(acknowledged)
        after = build_recovery_center(workspace_id="workspace_tps")
        self.assertEqual(0, after["attention_count"])
        self.assertTrue(after["items"][0]["acknowledged"])
        self.assertEqual("failed", get_run(str(run["run_id"]))["phase"])


class RestartCheckpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = prepare_control_plane_imports()
        self.addCleanup(self._restore)
        from app.persistence import run_store, task_store
        from app.platform_recovery.store import reset_store

        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        reset_store()
        self.addCleanup(task_store.reset_store)
        self.addCleanup(reset_store)

    def _restore(self) -> None:
        import sys as sys_mod

        for name in list(sys_mod.modules):
            if name == "app" or name.startswith("app."):
                sys_mod.modules.pop(name, None)
        sys_mod.modules.update(self._saved)

    def test_checkpointed_employee_run_is_paused_not_cancelled(self) -> None:
        from app.persistence import run_store, task_store
        from app.platform_recovery.checkpoints import write_checkpoint
        from app.runs.restart_reconcile import reconcile_orphaned_runs_on_startup
        from app.runs.service import create_run, resume_run

        opened = task_store.create_task(
            workspace_id="workspace_tps",
            goal="Preserve progress",
            owner_role="lead",
        )
        leased = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_tps-lead",
        )
        run = create_run(
            workspace_id="workspace_tps",
            mode="agent",
            summary="Lead shift with checkpoint",
            employee_role="lead",
            task_id=leased["task_id"],
            require_leased_task=True,
        )
        write_checkpoint(
            str(run["run_id"]),
            {
                "task_id": leased["task_id"],
                "workspace_id": "workspace_tps",
                "current_stage": "executing",
                "changed_paths": ["docs/plan.md"],
            },
        )
        reconciled = reconcile_orphaned_runs_on_startup(boot_id="boot_test")
        self.assertIn(str(run["run_id"]), reconciled)
        stored = run_store.get_run(str(run["run_id"]))
        assert stored is not None
        self.assertEqual("paused", stored.get("phase"))
        task = task_store.get_task(str(leased["task_id"]))
        assert task is not None
        self.assertEqual("leased", task.get("status"))
        resumed = resume_run(str(run["run_id"]))
        self.assertEqual("executing", resumed.get("phase"))

    def test_paused_checkpointed_run_projects_as_resumable(self) -> None:
        from app.persistence import run_store, task_store
        from app.platform_recovery.checkpoints import write_checkpoint
        from app.platform_recovery.projection import project_run_item
        from app.runs.restart_reconcile import reconcile_orphaned_runs_on_startup
        from app.runs.service import create_run

        opened = task_store.create_task(
            workspace_id="workspace_tps",
            goal="Show resumable in Recovery Center",
            owner_role="lead",
        )
        leased = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_tps-lead",
        )
        run = create_run(
            workspace_id="workspace_tps",
            mode="agent",
            summary="Lead shift with checkpoint",
            employee_role="lead",
            task_id=leased["task_id"],
            require_leased_task=True,
        )
        write_checkpoint(
            str(run["run_id"]),
            {
                "task_id": leased["task_id"],
                "workspace_id": "workspace_tps",
                "current_stage": "executing",
                "changed_paths": ["docs/plan.md"],
            },
        )
        reconcile_orphaned_runs_on_startup(boot_id="boot_project")
        stored = run_store.get_run(str(run["run_id"]))
        assert stored is not None
        item = project_run_item(stored)
        self.assertEqual("RESUMABLE", item["bucket"])
        self.assertIn("Resume", item["actions"])

    def test_second_restart_keeps_paused_checkpointed_run(self) -> None:
        from app.persistence import run_store, task_store
        from app.platform_recovery.checkpoints import write_checkpoint
        from app.runs.restart_reconcile import reconcile_orphaned_runs_on_startup
        from app.runs.service import create_run

        opened = task_store.create_task(
            workspace_id="workspace_tps",
            goal="Survive a second restart",
            owner_role="lead",
        )
        leased = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_tps-lead",
        )
        run = create_run(
            workspace_id="workspace_tps",
            mode="agent",
            summary="Lead shift with checkpoint",
            employee_role="lead",
            task_id=leased["task_id"],
            require_leased_task=True,
        )
        write_checkpoint(
            str(run["run_id"]),
            {
                "task_id": leased["task_id"],
                "workspace_id": "workspace_tps",
                "current_stage": "executing",
            },
        )
        reconcile_orphaned_runs_on_startup(boot_id="boot_one")
        reconcile_orphaned_runs_on_startup(boot_id="boot_two")
        stored = run_store.get_run(str(run["run_id"]))
        assert stored is not None
        self.assertEqual("paused", stored.get("phase"))
        task = task_store.get_task(str(leased["task_id"]))
        assert task is not None
        self.assertEqual("leased", task.get("status"))

    def test_restart_preview_marks_uncheckpointed_executing_as_non_resumable(self) -> None:
        from app.persistence import task_store
        from app.platform_recovery.restart import preview_restart_impact
        from app.runs.service import create_run

        opened = task_store.create_task(
            workspace_id="workspace_tps",
            goal="No checkpoint",
            owner_role="lead",
        )
        leased = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_tps-lead",
        )
        run = create_run(
            workspace_id="workspace_tps",
            mode="agent",
            summary="Lead shift without checkpoint",
            employee_role="lead",
            task_id=leased["task_id"],
            require_leased_task=True,
        )
        preview = preview_restart_impact()
        self.assertEqual("high", preview["risk"])
        ids = [item["run_id"] for item in preview["non_resumable_work"]]
        self.assertIn(str(run["run_id"]), ids)
        self.assertEqual([], preview["resumable_work"])


if __name__ == "__main__":
    unittest.main()
