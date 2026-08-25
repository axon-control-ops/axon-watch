"""Regression: stale failed-shift Needs-you cards must clear once the role recovers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_app_loader import prepare_control_plane_imports
from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


class AutonomousAttentionRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = prepare_control_plane_imports()
        self.addCleanup(self._restore)
        from app.persistence import autonomous_attention_store, run_store

        isolate_control_plane_db(self, run_store)
        autonomous_attention_store.reset_store()

    def _restore(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.modules.update(self._saved)

    def test_recovered_role_supersedes_the_real_production_dedupe_key_format(self) -> None:
        """collect_failed_shift_findings keys as "failed_shift:{workspace}:{role}"
        with no run_id (see lead_team_checkin.py) — the reconciler must parse
        that exact shape, not a hypothetical "...:{role}:{run_id}" one.
        """
        from app.persistence import autonomous_attention_store
        from app.workspace_agents.autonomous_attention_recovery import (
            reconcile_recovered_failed_shift_decisions,
        )

        receipt = autonomous_attention_store.append_receipt(
            kind="operator_blocker",
            decision="escalate",
            tier="operator_gated",
            risk="high",
            title="Cass (watcher) last shift failed",
            detail="Codex/OpenAI API key was rejected. [run=run_8243b72be74b]",
            dedupe_key="failed_shift:workspace_dashpro:watcher",
            workspace_id="workspace_dashpro",
            ask_operator=True,
            payload={"owner_role": "watcher"},
        )
        pending = autonomous_attention_store.list_pending_decisions(limit=50)
        self.assertEqual(1, len(pending))

        def fake_latest_outcome(workspace_id: str, role: str) -> dict[str, str] | None:
            self.assertEqual("workspace_dashpro", workspace_id)
            self.assertEqual("watcher", role)
            return {
                "run_id": "run_newer_success",
                "outcome": "completed",
                "detail": "",
                "phase": "completed",
                "terminal": "1",
            }

        reconcile_recovered_failed_shift_decisions(
            "workspace_dashpro",
            pending,
            latest_outcome=fake_latest_outcome,
        )

        remaining = autonomous_attention_store.list_pending_decisions(limit=50)
        self.assertEqual(
            [],
            remaining,
            "stale Needs-you card must clear once the role's latest run is completed",
        )

    def test_still_failing_role_is_left_pending(self) -> None:
        from app.persistence import autonomous_attention_store
        from app.workspace_agents.autonomous_attention_recovery import (
            reconcile_recovered_failed_shift_decisions,
        )

        autonomous_attention_store.append_receipt(
            kind="operator_blocker",
            decision="escalate",
            tier="operator_gated",
            risk="high",
            title="Cass (watcher) last shift failed",
            detail="Codex/OpenAI API key was rejected. [run=run_8243b72be74b]",
            dedupe_key="failed_shift:workspace_dashpro:watcher",
            workspace_id="workspace_dashpro",
            ask_operator=True,
            payload={"owner_role": "watcher"},
        )
        pending = autonomous_attention_store.list_pending_decisions(limit=50)

        def fake_latest_outcome(workspace_id: str, role: str) -> dict[str, str] | None:
            return {
                "run_id": "run_8243b72be74b",
                "outcome": "failed",
                "detail": "still failing",
                "phase": "failed",
                "terminal": "1",
            }

        reconcile_recovered_failed_shift_decisions(
            "workspace_dashpro",
            pending,
            latest_outcome=fake_latest_outcome,
        )

        remaining = autonomous_attention_store.list_pending_decisions(limit=50)
        self.assertEqual(1, len(remaining))

    def test_newer_completed_run_reconciles_decision_on_completion_event(self) -> None:
        from app.persistence import autonomous_attention_store
        from app.runs.service import complete_run, create_run, fail_run

        failed = create_run(
            workspace_id="workspace_dashpro",
            mode="agent",
            summary="Dana failed shift",
            employee_role="lead",
        )
        fail_run(str(failed["run_id"]), receipt_summary="runtime failed")
        autonomous_attention_store.append_receipt(
            kind="operator_blocker",
            decision="escalate",
            tier="operator_gated",
            risk="high",
            title="Dana (lead) last shift failed",
            detail=f"runtime failed [run={failed['run_id']}]",
            dedupe_key="failed_shift:workspace_dashpro:lead",
            workspace_id="workspace_dashpro",
            ask_operator=True,
            payload={
                "owner_role": "watcher",
                "subject_role": "lead",
                "subject_run_id": failed["run_id"],
            },
        )

        recovered = create_run(
            workspace_id="workspace_dashpro",
            mode="agent",
            summary="Dana recovered shift",
            employee_role="lead",
        )
        complete_run(str(recovered["run_id"]))

        self.assertEqual([], autonomous_attention_store.list_pending_decisions(limit=50))


if __name__ == "__main__":
    unittest.main()
