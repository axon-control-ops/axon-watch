"""Stale-signal diagnosis and next-best-action copy."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from tests.support.control_plane_app_loader import prepare_control_plane_imports


class StaleSignalTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = prepare_control_plane_imports()
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        import sys as sys_mod

        for name in list(sys_mod.modules):
            if name == "app" or name.startswith("app."):
                sys_mod.modules.pop(name, None)
        sys_mod.modules.update(self._saved)

    def test_heartbeat_without_progress_is_recovery_required(self) -> None:
        from app.platform_recovery.signals import diagnose_stale_run

        outcome = diagnose_stale_run(
            {"phase": "executing", "run_id": "run_1"},
            signals=["heartbeat_without_progress"],
            checkpoint=None,
            worker_alive=True,
        )
        self.assertEqual("RECOVERY_REQUIRED", outcome)

    def test_dead_worker_with_checkpoint_is_resumable(self) -> None:
        from app.platform_recovery.signals import diagnose_stale_run

        outcome = diagnose_stale_run(
            {"phase": "executing", "run_id": "run_1"},
            signals=["process_pid_missing"],
            checkpoint={
                "run_id": "run_1",
                "last_checkpoint_at": datetime.now(timezone.utc).isoformat(),
            },
            worker_alive=False,
        )
        self.assertEqual("RESUMABLE", outcome)

    def test_dead_worker_without_checkpoint_is_retryable(self) -> None:
        from app.platform_recovery.signals import diagnose_stale_run

        outcome = diagnose_stale_run(
            {"phase": "executing", "run_id": "run_1"},
            signals=["process_pid_missing"],
            checkpoint=None,
            worker_alive=False,
        )
        self.assertEqual("RETRYABLE", outcome)

    def test_unknown_liveness_is_stale_not_a_resume_guess(self) -> None:
        from app.platform_recovery.signals import diagnose_stale_run

        outcome = diagnose_stale_run(
            {"phase": "executing", "run_id": "run_1"},
            signals=["no_meaningful_progress"],
            checkpoint={
                "run_id": "run_1",
                "last_checkpoint_at": datetime.now(timezone.utc).isoformat(),
            },
            worker_alive=None,
        )
        self.assertEqual("RECOVERY_REQUIRED", outcome)

    def test_next_action_names_resume_safety(self) -> None:
        from app.platform_recovery.next_action import describe_next_action

        action = describe_next_action(
            bucket="STALE",
            failure_class="PROCESS_LOST",
            checkpoint_valid=True,
            idle_seconds=660,
        )
        self.assertEqual("RESUME", action["action"])
        self.assertIn("11 minutes ago", action["summary"])

    def test_circuit_opens_after_repeated_failures(self) -> None:
        from app.platform_recovery.circuit_breaker import allow_request, record_failure, record_success
        from app.platform_recovery.store import reset_store

        reset_store()
        self.addCleanup(reset_store)
        record_success("provider.ai")
        record_failure("provider.ai")
        record_failure("provider.ai")
        opened = record_failure("provider.ai")
        self.assertEqual("OPEN", opened["state"])
        self.assertFalse(allow_request("provider.ai"))


class OperationalInstructionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = prepare_control_plane_imports()
        self.addCleanup(self._restore)
        from app.persistence import run_store, task_store
        from app.platform_recovery.store import reset_store
        from tests.support.control_plane_db import isolate_control_plane_db

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

    def test_instructions_use_live_state_not_the_source_prompt(self) -> None:
        from app.platform_recovery.instructions import build_operational_instructions
        from app.runs.service import create_run

        run = create_run(
            workspace_id="workspace_tps",
            mode="agent",
            summary="Lead shift",
        )
        markdown = build_operational_instructions(
            workspace_id="workspace_tps",
            run_id=str(run["run_id"]),
        )
        self.assertIn("# Current Task", markdown)
        self.assertIn("Recommended Next Step", markdown)
        self.assertNotIn("You are a lead coding agent", markdown.lower())
        self.assertIn(str(run["run_id"]), markdown)


if __name__ == "__main__":
    unittest.main()
