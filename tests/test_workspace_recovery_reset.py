"""Focused regression coverage for guarded workspace recovery reset."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from tests.support.control_plane_app_loader import prepare_control_plane_imports
from tests.support.control_plane_db import isolate_control_plane_db


class WorkspaceRecoveryResetTests(unittest.TestCase):
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
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                sys.modules.pop(name, None)
        sys.modules.update(self._saved)

    def test_cancels_failed_run_retry_task_and_preserves_history(self) -> None:
        from app.persistence import run_store, task_store
        from app.platform_recovery.projection import build_recovery_center
        from app.platform_recovery.workspace_reset import reset_workspace_recovery_state
        from app.runs.service import create_run, fail_run

        opened = task_store.create_task(
            workspace_id="workspace_young_eagles_day_care",
            goal="Run integrations smoke test",
            owner_role="integrations",
        )
        leased = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_young_eagles_day_care-integrations",
        )
        run = create_run(
            workspace_id="workspace_young_eagles_day_care",
            mode="agent",
            summary="Integrations shift",
            employee_role="integrations",
            task_id=leased["task_id"],
            require_leased_task=True,
        )
        failed = fail_run(
            str(run["run_id"]),
            receipt_summary="Workspace delivery blocked: workspace delivery is not configured",
        )
        task_store.fail_task(
            str(leased["task_id"]),
            run_id=str(run["run_id"]),
            terminal_outcome="delivery blocked",
            reopen_if_budget_remaining=True,
        )
        history_ref = str(failed["history_ref"])
        history_size = len(run_store.list_history(history_ref))

        preview = reset_workspace_recovery_state(
            "workspace_young_eagles_day_care",
            execute=False,
        )
        self.assertEqual("DRY_RUN", preview["mode"])
        self.assertEqual([leased["task_id"]], preview["task_ids"])
        self.assertEqual("open", task_store.get_task(str(leased["task_id"]))["status"])

        result = reset_workspace_recovery_state(
            "workspace_young_eagles_day_care",
            execute=True,
        )
        self.assertEqual([], result["errors"])
        self.assertEqual([leased["task_id"]], result["cancelled_tasks"])
        self.assertEqual("cancelled", task_store.get_task(str(leased["task_id"]))["status"])
        self.assertEqual("failed", run_store.get_run(str(run["run_id"]))["phase"])
        self.assertEqual(history_size, len(run_store.list_history(history_ref)))
        self.assertEqual(
            0,
            build_recovery_center(
                workspace_id="workspace_young_eagles_day_care"
            )["attention_count"],
        )

    def test_stops_only_a_targeted_live_run(self) -> None:
        from app.persistence import run_store, task_store
        from app.platform_recovery.workspace_reset import reset_workspace_recovery_state
        from app.runs.service import create_run

        opened = task_store.create_task(
            workspace_id="workspace_young_eagles_day_care",
            goal="Recover stale integration worker",
            owner_role="integrations",
        )
        leased = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_young_eagles_day_care-integrations",
        )
        run = create_run(
            workspace_id="workspace_young_eagles_day_care",
            mode="agent",
            summary="Stale integrations shift",
            employee_role="integrations",
            task_id=leased["task_id"],
            require_leased_task=True,
        )
        item = {
            "actionable": True,
            "bucket": "STALE",
            "run_id": run["run_id"],
            "task_id": leased["task_id"],
            "recovery_id": "recovery_live",
        }
        with (
            patch(
                "app.platform_recovery.workspace_reset.build_recovery_center",
                return_value={"items": [item]},
            ),
            patch(
                "app.platform_recovery.workspace_reset.acknowledge_recovery",
                return_value={"recovery_id": "recovery_live", "acknowledged": True},
            ),
        ):
            result = reset_workspace_recovery_state(
                "workspace_young_eagles_day_care",
                execute=True,
            )

        self.assertEqual([run["run_id"]], result["cancelled_runs"])
        self.assertEqual([leased["task_id"]], result["cancelled_tasks"])
        self.assertEqual("cancelled", run_store.get_run(str(run["run_id"]))["phase"])
        self.assertEqual("cancelled", task_store.get_task(str(leased["task_id"]))["status"])

    def test_finds_an_old_lease_with_a_missing_run(self) -> None:
        from app.platform_recovery.workspace_reset import _is_orphaned_leased_task

        now = datetime.now(timezone.utc)
        task = {
            "status": "leased",
            "run_id": "run_missing",
            "updated_at": (now - timedelta(minutes=10)).isoformat(),
            "lease_expires_at": (now + timedelta(minutes=50)).isoformat(),
        }
        with patch(
            "app.platform_recovery.workspace_reset.run_store.get_run",
            return_value=None,
        ):
            self.assertTrue(_is_orphaned_leased_task(task, now=now))

        task["updated_at"] = (now - timedelta(minutes=1)).isoformat()
        with patch(
            "app.platform_recovery.workspace_reset.run_store.get_run",
            return_value=None,
        ):
            self.assertFalse(_is_orphaned_leased_task(task, now=now))


if __name__ == "__main__":
    unittest.main()
