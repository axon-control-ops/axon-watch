"""Lead team check-in scheduler + role assignment guardrails."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import autonomous_attention_store, run_store, task_store  # noqa: E402
from app.runs.service import create_run, fail_run  # noqa: E402
from app.workspace_agents.company_work_sources import list_enabled_work_sources  # noqa: E402
from app.workspace_agents.lead_team_checkin import (  # noqa: E402
    ASSIGN_GOAL_PREFIX,
    ATTEND_GOAL_PREFIX,
    LeadCheckinFinding,
    assign_owner_role_for_failed_shift,
    assign_owner_role_for_monitor,
    enqueue_lead_assignments,
    escalate_operator_blockers_to_vaxon,
    run_lead_team_checkin,
    workspace_due_for_checkin,
)
from app.workspace_agents.lead_checkin_report import (  # noqa: E402
    format_lead_checkin_message,
    humanize_lead_failure_detail,
)


class LeadAssignmentGuardrailTests(unittest.TestCase):
    def test_monitor_role_mapping(self) -> None:
        self.assertEqual("watcher", assign_owner_role_for_monitor("sentry_recent_issues", "Sentry"))
        self.assertEqual(
            "integrations",
            assign_owner_role_for_monitor("posthog_recent_events", "PostHog"),
        )
        self.assertEqual(
            "watcher",
            assign_owner_role_for_monitor("http_health", "GitHub API"),
        )
        self.assertEqual("backend", assign_owner_role_for_monitor("http_health", "Control plane"))

    def test_usage_limit_escalates_only(self) -> None:
        role, escalate = assign_owner_role_for_failed_shift(
            "frontend",
            "Out of usage — increase limits in Cursor",
        )
        self.assertEqual("frontend", role)
        self.assertTrue(escalate)

    def test_billing_failure_escalates_only(self) -> None:
        # Regression: billing/credit failures used to fall through to the
        # default (auto-dispatch) branch, so the Lead kept assigning fresh
        # specialist tasks to retry work that could never succeed until the
        # account was fixed — burning a full dispatch every cycle.
        role, escalate = assign_owner_role_for_failed_shift(
            "backend",
            "Credit balance is too low",
        )
        self.assertEqual("backend", role)
        self.assertTrue(escalate)

        role, escalate = assign_owner_role_for_failed_shift(
            "integrations",
            "ActionRequiredError: You have an unpaid invoice",
        )
        self.assertEqual("integrations", role)
        self.assertTrue(escalate)

    def test_unpaid_invoice_escalates_only(self) -> None:
        role, escalate = assign_owner_role_for_failed_shift(
            "integrations",
            "ActionRequiredError: You have an unpaid invoice Visit cursor.com/dashboard",
        )
        self.assertEqual("integrations", role)
        self.assertTrue(escalate)

    def test_crc_failure_reassigns_same_role(self) -> None:
        role, escalate = assign_owner_role_for_failed_shift(
            "watcher",
            "Critical Review Clause missing Confidence: N/10",
        )
        self.assertEqual("watcher", role)
        self.assertFalse(escalate)


class LeadTeamCheckinTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        autonomous_attention_store.reset_store()
        self.addCleanup(task_store.reset_store)
        self.addCleanup(autonomous_attention_store.reset_store)
        self.state_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.state_dir.cleanup)
        self.state_path = Path(self.state_dir.name) / "lead-team-checkin.json"

    def test_config_lists_lead_checkin_source(self) -> None:
        ids = {str(item.get("id")) for item in list_enabled_work_sources(REPO_ROOT)}
        self.assertIn("lead_team_checkin", ids)

    def test_enqueue_assigns_specialist_and_dedupes(self) -> None:
        findings = [
            LeadCheckinFinding(
                kind="failed_shift",
                workspace_id="workspace_dashpro",
                owner_role="watcher",
                title="Cass (watcher) last shift failed",
                detail="Critical Review Clause missing",
                dedupe_key="failed_shift:workspace_dashpro:watcher:run_1",
            )
        ]
        first = enqueue_lead_assignments(
            workspace_id="workspace_dashpro",
            findings=findings,
            max_new_tasks=2,
        )
        self.assertEqual(1, len(first))
        self.assertTrue(first[0]["goal"].startswith(ASSIGN_GOAL_PREFIX))
        self.assertEqual("watcher", first[0]["owner_role"])
        second = enqueue_lead_assignments(
            workspace_id="workspace_dashpro",
            findings=findings,
            max_new_tasks=2,
        )
        self.assertEqual(0, len(second))

    def test_usage_blocker_does_not_create_task(self) -> None:
        findings = [
            LeadCheckinFinding(
                kind="operator_blocker",
                workspace_id="workspace_dashpro",
                owner_role="frontend",
                title="Priya usage blocked",
                detail="Out of usage",
                dedupe_key="failed_shift:workspace_dashpro:frontend:run_2",
                escalate_only=True,
            )
        ]
        created = enqueue_lead_assignments(
            workspace_id="workspace_dashpro",
            findings=findings,
            max_new_tasks=2,
        )
        self.assertEqual([], created)

    def test_cooldown_and_checkin_tick(self) -> None:
        self.assertTrue(
            workspace_due_for_checkin(
                "workspace_axon_watch",
                min_interval_seconds=900,
                state_path=self.state_path,
            )
        )
        with patch(
            "app.workspace_agents.lead_team_checkin.collect_workspace_findings",
            return_value=[
                LeadCheckinFinding(
                    kind="monitor_alert",
                    workspace_id="workspace_axon_watch",
                    owner_role="integrations",
                    title="GitHub API monitor warning",
                    detail="HTTP 502",
                    dedupe_key="monitor:workspace_axon_watch:axon_x_github_api_health:warning",
                )
            ],
        ), patch(
            "app.workspace_agents.lead_team_checkin._post_lead_checkin_message",
            return_value="message_test",
        ):
            result = run_lead_team_checkin(
                min_interval_seconds=900,
                max_assignments_per_workspace=1,
                workspace_ids=["workspace_axon_watch"],
                state_path=self.state_path,
                post_lead_message=True,
            )
        self.assertIn("workspace_axon_watch", result["checked_workspaces"])
        self.assertEqual(1, len(result["created_tasks"]))
        self.assertFalse(
            workspace_due_for_checkin(
                "workspace_axon_watch",
                min_interval_seconds=900,
                state_path=self.state_path,
            )
        )
        again = run_lead_team_checkin(
            min_interval_seconds=900,
            workspace_ids=["workspace_axon_watch"],
            state_path=self.state_path,
        )
        self.assertIn("workspace_axon_watch", again["skipped_cooldown"])

    def test_failed_lead_shift_escalates_to_vaxon_without_specialist_task(self) -> None:
        run = create_run(
            workspace_id="workspace_dashpro",
            mode="agent",
            summary="Dana lead shift",
            employee_role="lead",
        )
        fail_run(
            str(run["run_id"]),
            receipt_summary="Workspace delivery blocked: no publishable changes",
        )

        with patch(
            "app.workspace_agents.lead_team_checkin._post_lead_checkin_message",
            return_value="message_test",
        ):
            result = run_lead_team_checkin(
                min_interval_seconds=0,
                max_assignments_per_workspace=2,
                workspace_ids=["workspace_dashpro"],
                state_path=self.state_path,
                post_lead_message=True,
            )

        self.assertEqual([], result["created_tasks"])
        self.assertEqual(1, len(result["escalated"]))
        receipt = result["escalated"][0]
        self.assertTrue(receipt["ask_operator"])
        self.assertEqual("operator_blocker", receipt["kind"])
        self.assertIn("lead", receipt["title"].lower())
        self.assertIn("must not remain stuck", receipt["detail"])

    def test_leased_approved_recovery_task_suppresses_repeat_lead_failure_card(self) -> None:
        dedupe_key = "failed_shift:workspace_axon_watch:lead"
        recovery = task_store.create_task(
            workspace_id="workspace_axon_watch",
            goal=(
                f"{ATTEND_GOAL_PREFIX} Operator approved: "
                f"Mira (lead) last shift failed. [{dedupe_key}]"
            ),
            acceptance_criteria=(
                "Exact approved effect: recover the lead failure. "
                f"dedupe={dedupe_key}"
            ),
            risk="approved",
            owner_role="watcher",
            attempt_budget=1,
        )
        recovery = task_store.lease_task(
            str(recovery["task_id"]),
            lease_holder="worker-test",
            lease_seconds=300,
            run_id="run_recovery",
        )

        findings = [
            LeadCheckinFinding(
                kind="operator_blocker",
                workspace_id="workspace_axon_watch",
                owner_role="watcher",
                title="Mira (lead) last shift failed",
                detail="acceptance_evidence did not pass (Gate 6) [run=run_failed]",
                dedupe_key=dedupe_key,
                escalate_only=True,
            )
        ]

        escalated = escalate_operator_blockers_to_vaxon(
            workspace_id="workspace_axon_watch",
            findings=findings,
        )

        self.assertEqual([], escalated)
        self.assertEqual([], autonomous_attention_store.list_pending_decisions(limit=50))
        self.assertEqual("leased", task_store.get_task(str(recovery["task_id"]))["status"])


class LeadCheckinReportTests(unittest.TestCase):
    def test_formats_gate6_finding_with_next_steps(self) -> None:
        findings = [
            LeadCheckinFinding(
                kind="failed_shift",
                workspace_id="workspace_dashpro",
                owner_role="frontend",
                title="Priya (frontend) last shift failed",
                detail=(
                    "Lane B finalization failed: acceptance_evidence did not pass "
                    "[Gate 6] | policy=out_of_scope [run=run_abc]"
                ),
                dedupe_key="failed_shift:workspace_dashpro:frontend",
            )
        ]
        body = format_lead_checkin_message(findings, [])
        self.assertIn("Lead check-in:", body)
        self.assertIn("[failed_shift] Priya (frontend) last shift failed (→ frontend)", body)
        self.assertIn("out of scope", humanize_lead_failure_detail(findings[0].detail).lower())
        self.assertIn("## Next steps", body)
        self.assertIn("Inspect Priya", body)


if __name__ == "__main__":
    unittest.main()
