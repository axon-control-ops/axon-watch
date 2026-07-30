"""Attend loop dispatch vs escalate proofs."""

from __future__ import annotations

import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import (  # noqa: E402
    autonomous_attention_store,
    handoff_store,
    operator_presence_settings_store,
    task_store,
)
from app.workspace_agents.autonomous_attention import (  # noqa: E402
    ATTEND_GOAL_PREFIX,
    collect_handoff_findings,
    enqueue_attend_actions,
    resolve_autonomy_decision,
)
from app.workspace_agents.lead_checkin_assign import LeadCheckinFinding  # noqa: E402
from app.workspace_agents.lead_team_checkin import enqueue_lead_assignments  # noqa: E402


class AutonomousAttentionLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, task_store)
        autonomous_attention_store.reset_store()

    def test_github_email_ci_noise_does_not_create_attend_task(self) -> None:
        findings = [
            LeadCheckinFinding(
                kind="warning_signal",
                workspace_id="workspace_axon_watch",
                owner_role="watcher",
                title=(
                    "Email needs follow-up: [axon-control-ops/dashpro] "
                    "PR run failed: Android CI/CD Pipeline"
                ),
                detail="GitHub check-suites mail",
                dedupe_key=(
                    "signal:workspace_axon_watch:"
                    "signal_email_axon-control-ops_dashpro_check-suites_CS_x:warning"
                ),
            )
        ]
        result = enqueue_attend_actions(
            workspace_id="workspace_axon_watch",
            findings=findings,
        )
        self.assertEqual(result["created_tasks"], [])
        self.assertEqual(result["escalated"], [])
        self.assertTrue(
            any(item.get("reason") == "email_ci_noise_no_dispatch" for item in result["skipped"])
        )

    def test_lead_assignment_sees_existing_attend_task_dedupe(self) -> None:
        dedupe = "failed_shift:workspace_axon_watch:watcher:run_dup"
        task_store.create_task(
            workspace_id="workspace_axon_watch",
            goal=f"{ATTEND_GOAL_PREFIX} Rowan (watcher) last shift failed. [{dedupe}]",
            acceptance_criteria=f"dedupe={dedupe}",
            risk="normal",
            owner_role="watcher",
        )
        created = enqueue_lead_assignments(
            workspace_id="workspace_axon_watch",
            findings=[
                LeadCheckinFinding(
                    kind="failed_shift",
                    workspace_id="workspace_axon_watch",
                    owner_role="watcher",
                    title="Rowan (watcher) last shift failed",
                    detail="failed",
                    dedupe_key=dedupe,
                )
            ],
            max_new_tasks=2,
        )
        self.assertEqual(created, [])

    def test_warning_and_handoff_dispatch_safe_tasks(self) -> None:
        findings = [
            LeadCheckinFinding(
                kind="warning_signal",
                workspace_id="workspace_axon_watch",
                owner_role="watcher",
                title="Fast Gate failed",
                detail="Typecheck",
                dedupe_key="signal:workspace_axon_watch:fg1:high",
            ),
            LeadCheckinFinding(
                kind="open_handoff",
                workspace_id="workspace_axon_watch",
                owner_role="backend",
                title="Handoff follow-through: repair auth",
                detail="Finish auth ticket",
                dedupe_key="handoff:handoff-1",
            ),
        ]
        result = enqueue_attend_actions(
            workspace_id="workspace_axon_watch",
            findings=findings,
            max_dispatch=4,
        )
        self.assertEqual(len(result["created_tasks"]), 2)
        self.assertEqual(result["escalated"], [])
        goals = [str(row.get("goal") or "") for row in result["created_tasks"]]
        self.assertTrue(all(goal.startswith(ATTEND_GOAL_PREFIX) for goal in goals))
        for row in result["created_tasks"]:
            self.assertEqual(row.get("risk"), "normal")
        claimed = task_store.claim_open_task_for_role(
            workspace_id="workspace_axon_watch",
            owner_role="watcher",
            lease_holder="employee-workspace_axon_watch-watcher",
        )
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(claimed["task_id"], result["created_tasks"][0]["task_id"])

    def test_critical_item_escalates_without_leaseable_task(self) -> None:
        findings = [
            LeadCheckinFinding(
                kind="critical_signal",
                workspace_id="workspace_axon_watch",
                owner_role="watcher",
                title="Production deploy blocked",
                detail="Needs operator",
                dedupe_key="signal:workspace_axon_watch:crit1:critical",
                escalate_only=True,
            )
        ]
        result = enqueue_attend_actions(
            workspace_id="workspace_axon_watch",
            findings=findings,
        )
        self.assertEqual(result["created_tasks"], [])
        self.assertEqual(len(result["escalated"]), 1)
        self.assertTrue(result["escalated"][0]["ask_operator"])
        open_tasks = task_store.list_tasks(
            workspace_id="workspace_axon_watch", status="open"
        )
        self.assertEqual(open_tasks, [])
        receipt = result["escalated"][0]
        approved = resolve_autonomy_decision(
            receipt["receipt_id"],
            resolution="approved",
        )
        self.assertEqual(approved["status"], "resolved")
        self.assertEqual(approved["resolution"], "approved")
        task = task_store.get_task(str(approved["task_id"]))
        assert task is not None
        self.assertEqual(task["risk"], "approved")
        self.assertEqual(task["approval_receipt_id"], receipt["receipt_id"])
        claimed = task_store.claim_open_task_for_role(
            workspace_id="workspace_axon_watch",
            owner_role="watcher",
            lease_holder="employee-workspace_axon_watch-watcher",
        )
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(claimed["task_id"], task["task_id"])

    def test_dedupe_skips_second_pass(self) -> None:
        finding = LeadCheckinFinding(
            kind="warning_signal",
            workspace_id="workspace_axon_watch",
            owner_role="watcher",
            title="Fast Gate failed",
            detail="Typecheck",
            dedupe_key="signal:workspace_axon_watch:fg-dedupe:high",
        )
        first = enqueue_attend_actions(
            workspace_id="workspace_axon_watch",
            findings=[finding],
        )
        second = enqueue_attend_actions(
            workspace_id="workspace_axon_watch",
            findings=[finding],
        )
        self.assertEqual(len(first["created_tasks"]), 1)
        self.assertEqual(second["created_tasks"], [])
        self.assertTrue(any(item.get("reason") == "deduped" for item in second["skipped"]))

    def test_claim_skips_high_risk_open_task(self) -> None:
        high = task_store.create_task(
            workspace_id="workspace_axon_watch",
            goal="Dangerous: rotate production secret",
            acceptance_criteria="do not auto",
            risk="high",
            owner_role="watcher",
        )
        normal = task_store.create_task(
            workspace_id="workspace_axon_watch",
            goal="Safe file-size split",
            acceptance_criteria="split module",
            risk="normal",
            owner_role="watcher",
        )
        claimed = task_store.claim_open_task_for_role(
            workspace_id="workspace_axon_watch",
            owner_role="watcher",
            lease_holder="employee-workspace_axon_watch-watcher",
        )
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(claimed["task_id"], normal["task_id"])
        still_open = task_store.get_task(high["task_id"])
        assert still_open is not None
        self.assertEqual(still_open["status"], "open")

    def test_dangerous_monitor_escalates_before_task_creation(self) -> None:
        finding = LeadCheckinFinding(
            kind="monitor_alert",
            workspace_id="workspace_axon_watch",
            owner_role="watcher",
            title="Repair repository with git reset --hard",
            detail="Destructive recovery requested",
            dedupe_key="monitor:dangerous",
        )
        result = enqueue_attend_actions(
            workspace_id="workspace_axon_watch",
            findings=[finding],
        )
        self.assertEqual(result["created_tasks"], [])
        self.assertEqual(len(result["escalated"]), 1)
        self.assertEqual(
            enqueue_lead_assignments(
                workspace_id="workspace_axon_watch",
                findings=[finding],
            ),
            [],
        )

    def test_handoff_reuses_existing_target_task_and_ignores_source(self) -> None:
        handoff = {
            "handoff_id": "handoff-routed",
            "source_workspace_id": "workspace_source",
            "target_workspace_id": "workspace_target",
            "task": "Fix target API",
            "routed_role": "backend",
            "target_task_id": "task-existing",
        }
        self.assertEqual(
            collect_handoff_findings("workspace_source", handoffs=[handoff]),
            [],
        )
        self.assertEqual(
            collect_handoff_findings("workspace_target", handoffs=[handoff]),
            [],
        )

    def test_missing_handoff_route_is_persisted_after_task_creation(self) -> None:
        handoff = handoff_store.create_handoff_record(
            source_workspace_id="workspace_source",
            target_workspace_id="workspace_axon_watch",
            task="Repair target API",
        )
        findings = collect_handoff_findings(
            "workspace_axon_watch",
            handoffs=[handoff],
        )
        result = enqueue_attend_actions(
            workspace_id="workspace_axon_watch",
            findings=findings,
        )
        self.assertEqual(len(result["created_tasks"]), 1)
        updated = handoff_store.get_handoff(str(handoff["handoff_id"]))
        assert updated is not None
        self.assertEqual(
            updated["target_task_id"],
            result["created_tasks"][0]["task_id"],
        )
        self.assertEqual(updated["status"], "routed")

    def test_dedupe_expires_but_pending_decision_remains_deduped(self) -> None:
        with patch.object(
            autonomous_attention_store,
            "_utc_now_iso",
            return_value="2020-01-01T00:00:00Z",
        ):
            autonomous_attention_store.append_receipt(
                kind="warning_signal",
                decision="dispatch",
                tier="auto_safe",
                dedupe_key="old-warning",
            )
            autonomous_attention_store.append_receipt(
                kind="critical_signal",
                decision="escalate",
                tier="operator_gated",
                risk="critical",
                dedupe_key="old-pending",
                ask_operator=True,
            )
        self.assertFalse(
            autonomous_attention_store.has_recent_dedupe_key("old-warning")
        )
        self.assertTrue(
            autonomous_attention_store.has_recent_dedupe_key("old-pending")
        )

    def test_receipts_redact_secret_values(self) -> None:
        receipt = autonomous_attention_store.append_receipt(
            kind="secrets_blocker",
            decision="escalate",
            tier="operator_gated",
            risk="dangerous",
            title="GH_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz123456",
            detail="Authorization: Bearer abcdefghijklmnopqrstuvwxyz",
            dedupe_key="token:dedupe-secret-value",
            ask_operator=True,
            payload={"password": "plain-secret-value"},
        )
        serialized = str(receipt)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz123456", serialized)
        self.assertNotIn("plain-secret-value", serialized)
        self.assertNotIn("dedupe-secret-value", serialized)
        self.assertIn("[REDACTED]", serialized)

    def test_status_and_decision_routes_use_pending_lifecycle(self) -> None:
        operator_presence_settings_store.save_settings(
            {
                **operator_presence_settings_store.load_settings(),
                "autonomy_mode": "full",
            }
        )
        pending = autonomous_attention_store.append_receipt(
            kind="critical_signal",
            decision="escalate",
            tier="operator_gated",
            risk="critical",
            title="Critical decision",
            detail="Exact guarded effect",
            workspace_id="workspace_axon_watch",
            dedupe_key="critical:route",
            ask_operator=True,
            payload={"owner_role": "watcher", "reason": "critical_severity"},
        )
        for index in range(12):
            autonomous_attention_store.append_receipt(
                kind="critical_signal",
                decision="escalate",
                tier="operator_gated",
                risk="critical",
                title=f"Other workspace {index}",
                workspace_id="workspace_other",
                dedupe_key=f"critical:other:{index}",
                ask_operator=True,
            )
        with TestClient(app) as client:
            status = client.get(
                "/api/operator/autonomy/status",
                params={"workspace_id": "workspace_axon_watch"},
            )
            self.assertEqual(status.status_code, 200)
            payload = status.json()
            self.assertTrue(payload["autonomous_enabled"])
            self.assertEqual(payload["pending_critical_count"], 1)
            self.assertEqual(len(payload["pending_critical_decisions"]), 1)
            resolved = client.post(
                f"/api/operator/autonomy/decisions/{pending['receipt_id']}",
                json={"resolution": "rejected"},
            )
            self.assertEqual(resolved.status_code, 200)
            self.assertEqual(resolved.json()["resolution"], "rejected")
            after = client.get(
                "/api/operator/autonomy/status",
                params={"workspace_id": "workspace_axon_watch"},
            ).json()
            self.assertEqual(after["pending_critical_decisions"], [])

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


if __name__ == "__main__":
    unittest.main()
