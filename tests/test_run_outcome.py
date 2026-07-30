"""Roster outcome helpers expose real failure detail, not bare FAILED."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store  # noqa: E402
from app.runs.service import create_run, fail_run, stop_run  # noqa: E402
from app.workspace_agents.run_outcome import latest_role_run_outcome  # noqa: E402


class RunOutcomeTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_fail_run_current_step_keeps_reason(self) -> None:
        created = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: continuous worker shift",
            employee_role="backend",
        )
        failed = fail_run(
            created["run_id"],
            receipt_summary="Lane B agent fallback reply generated (ActionRequiredError: out of usage)",
        )
        self.assertEqual("failed", failed["phase"])
        self.assertIn("out of usage", failed["current_step"])
        self.assertNotEqual("Run failed", failed["current_step"])

    def test_latest_role_outcome_reads_failure_receipt(self) -> None:
        created = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Shell Craft: continuous worker shift",
            employee_role="frontend",
        )
        fail_run(
            created["run_id"],
            receipt_summary="Lane B agent fallback reply generated (ActionRequiredError: out of usage)",
        )
        outcome = latest_role_run_outcome("workspace_axon_watch", "frontend")
        assert outcome is not None
        self.assertEqual("failed", outcome["outcome"])
        self.assertIn("out of usage", outcome["detail"])

    def test_latest_role_outcome_normalizes_lane_b_fallback_wrapper(self) -> None:
        created = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: continuous worker shift",
            employee_role="backend",
        )
        fail_run(
            created["run_id"],
            receipt_summary=(
                "Lane B agent fallback reply generated "
                "(ActionRequiredError: Increase limits for faster responses You're out of usage.)"
            ),
        )
        outcome = latest_role_run_outcome("workspace_axon_watch", "backend")
        assert outcome is not None
        self.assertEqual("failed", outcome["outcome"])
        self.assertNotIn("Lane B agent fallback", outcome["detail"])
        self.assertIn("out of usage", outcome["detail"])

    def test_latest_role_outcome_prefers_terminal_failure_over_paused_shift(self) -> None:
        failed = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Backend: continuous worker shift",
            employee_role="backend",
        )
        fail_run(
            failed["run_id"],
            receipt_summary="cursor agent unavailable",
        )

        paused = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Backend: follow-up shift",
            employee_role="backend",
        )
        stop_run(paused["run_id"])

        outcome = latest_role_run_outcome("workspace_axon_watch", "backend")
        assert outcome is not None
        self.assertEqual("failed", outcome["outcome"])
        self.assertIn("cursor agent unavailable", outcome["detail"])

    def test_latest_role_outcome_reads_failure_detail_from_history(self) -> None:
        created = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Integrations: connector parity shift",
            employee_role="integrations",
        )
        fail_run(
            created["run_id"],
            receipt_summary="control_plane probe unavailable (Connection refused)",
        )
        stored = run_store.get_run(created["run_id"])
        assert stored is not None
        stored["current_step"] = "Run failed"
        run_store.save_run(stored)

        outcome = latest_role_run_outcome("workspace_axon_watch", "integrations")
        assert outcome is not None
        self.assertEqual("failed", outcome["outcome"])
        self.assertIn("Connection refused", outcome["detail"])

    def test_latest_role_outcome_skips_control_plane_restart_interruptions(self) -> None:
        real_failure = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Rowan: connector health shift",
            employee_role="watcher",
        )
        fail_run(
            real_failure["run_id"],
            receipt_summary="control_plane probe unavailable (Connection refused)",
        )

        restarted = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Rowan: continuous worker shift",
            employee_role="watcher",
        )
        fail_run(
            restarted["run_id"],
            receipt_summary="Run interrupted by control-plane restart",
            actor="control-plane",
        )

        outcome = latest_role_run_outcome("workspace_axon_watch", "watcher")
        assert outcome is not None
        self.assertEqual("failed", outcome["outcome"])
        self.assertIn("Connection refused", outcome["detail"])
        self.assertEqual(real_failure["run_id"], outcome["run_id"])

    def test_latest_role_outcome_omits_restart_only_failure(self) -> None:
        restarted = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Rowan: continuous worker shift",
            employee_role="watcher",
        )
        fail_run(
            restarted["run_id"],
            receipt_summary="Run interrupted by control-plane restart",
            actor="control-plane",
        )

        self.assertIsNone(latest_role_run_outcome("workspace_axon_watch", "watcher"))

    def test_latest_role_outcome_skips_employee_restart_cancelled_run(self) -> None:
        real_failure = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Reed: backend shift",
            employee_role="backend",
        )
        fail_run(
            real_failure["run_id"],
            receipt_summary="verify:contracts — test_run_outcome.py: assertion failed",
        )

        restarted = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Reed: continuous worker shift",
            employee_role="backend",
        )
        from app.runs.restart_reconcile import interrupt_run_on_restart

        cancelled = interrupt_run_on_restart(restarted["run_id"])
        assert cancelled is not None
        self.assertEqual("cancelled", cancelled["phase"])

        outcome = latest_role_run_outcome("workspace_axon_watch", "backend")
        assert outcome is not None
        self.assertEqual("failed", outcome["outcome"])
        self.assertIn("assertion failed", outcome["detail"])
        self.assertEqual(real_failure["run_id"], outcome["run_id"])

    def test_latest_role_outcome_recovers_untagged_ide_completion_via_thread(self) -> None:
        from app.persistence import chat_store
        from app.runs.service import complete_run

        chat_store.reset_store()
        self.addCleanup(chat_store.reset_store)

        failed = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Marco: continuous worker shift",
            employee_role="backend",
        )
        fail_run(
            failed["run_id"],
            receipt_summary="Critical Review Clause missing: Confidence: N/10",
        )

        # Successful IDE retry historically omitted employee_role on the run row.
        completed = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Marco: bounded shift retry",
            employee_role=None,
        )
        complete_run(completed["run_id"])
        chat_store.create_thread(
            workspace_id="workspace_axon_watch",
            run_id=completed["run_id"],
            created_at="2026-07-26T10:00:16Z",
            thread_kind="ide",
            employee_id="employee-workspace_axon_watch-backend-3",
            employee_role="backend",
        )

        outcome = latest_role_run_outcome("workspace_axon_watch", "backend")
        assert outcome is not None
        self.assertEqual("completed", outcome["outcome"])
        self.assertEqual(completed["run_id"], outcome["run_id"])
        healed = run_store.get_run(completed["run_id"])
        assert healed is not None
        self.assertEqual("backend", healed.get("employee_role"))

if __name__ == "__main__":
    unittest.main()
