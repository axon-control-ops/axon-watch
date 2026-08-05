"""Concurrency and twin-deduplication proofs for autonomous attention."""

from __future__ import annotations

import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import autonomous_attention_store, task_store  # noqa: E402
from app.workspace_agents.autonomous_attention import (  # noqa: E402
    build_autonomy_status_feed,
    enqueue_attend_actions,
    resolve_autonomy_decision,
)
from app.workspace_agents.lead_checkin_assign import LeadCheckinFinding  # noqa: E402


class AutonomousAttentionConcurrencyTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, task_store)
        autonomous_attention_store.reset_store()

    def test_concurrent_scans_create_one_task(self) -> None:
        finding = LeadCheckinFinding(
            kind="warning_signal",
            workspace_id="workspace_axon_watch",
            owner_role="watcher",
            title="Concurrent warning",
            detail="One repair only",
            dedupe_key="signal:concurrent",
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(
                    lambda _: enqueue_attend_actions(
                        workspace_id="workspace_axon_watch",
                        findings=[finding],
                    ),
                    range(2),
                )
            )
        self.assertEqual(
            sum(len(result["created_tasks"]) for result in results),
            1,
        )

    def test_concurrent_approval_creates_one_approved_task(self) -> None:
        pending = autonomous_attention_store.append_receipt(
            kind="critical_signal",
            decision="escalate",
            tier="operator_gated",
            risk="critical",
            title="Concurrent approval",
            detail="One exact task",
            workspace_id="workspace_axon_watch",
            dedupe_key="critical:concurrent",
            ask_operator=True,
            payload={"owner_role": "watcher"},
        )

        def approve(_: int) -> str:
            try:
                result = resolve_autonomy_decision(
                    pending["receipt_id"],
                    resolution="approved",
                )
                return str(result["task_id"])
            except ValueError:
                return "blocked"

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(approve, range(2)))
        self.assertEqual(outcomes.count("blocked"), 1)
        tasks = task_store.list_tasks(workspace_id="workspace_axon_watch")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["risk"], "approved")

    def test_failed_shift_twins_collapse_and_clear_together(self) -> None:
        first = autonomous_attention_store.append_receipt(
            kind="failed_shift",
            decision="escalate",
            tier="operator_gated",
            risk="critical",
            title="Marco (backend) last shift failed",
            detail="run A",
            workspace_id="workspace_dashpro",
            dedupe_key="failed_shift:workspace_dashpro:backend:run_a",
            ask_operator=True,
            payload={"owner_role": "backend"},
        )
        autonomous_attention_store.append_receipt(
            kind="failed_shift",
            decision="escalate",
            tier="operator_gated",
            risk="critical",
            title="Marco (backend) last shift failed",
            detail="run B",
            workspace_id="workspace_dashpro",
            dedupe_key="failed_shift:workspace_dashpro:backend:run_b",
            ask_operator=True,
            payload={"owner_role": "backend"},
        )
        feed = build_autonomy_status_feed(workspace_id="workspace_dashpro")
        self.assertEqual(feed["pending_critical_count"], 1)
        self.assertEqual(len(feed["pending_critical_decisions"]), 1)
        resolve_autonomy_decision(first["receipt_id"], resolution="rejected")
        after = build_autonomy_status_feed(workspace_id="workspace_dashpro")
        self.assertEqual(after["pending_critical_decisions"], [])
        self.assertEqual(after["pending_critical_count"], 0)


if __name__ == "__main__":
    unittest.main()
