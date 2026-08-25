"""Bounded autonomy safety tiers and lease gates."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.autonomous_attention_policy import (  # noqa: E402
    classify_attention_item,
    normalize_task_risk,
    task_allows_autonomous_lease,
)


class AutonomousAttentionPolicyTests(unittest.TestCase):
    def test_warning_signal_is_auto_safe(self) -> None:
        decision = classify_attention_item(
            kind="warning_signal",
            title="Fast Gate failed",
            detail="Typecheck ratchet",
            severity="high",
        )
        self.assertEqual(decision.decision, "dispatch")
        self.assertEqual(decision.tier, "auto_safe")
        self.assertFalse(decision.ask_operator)

    def test_investigatory_critical_signal_auto_dispatches(self) -> None:
        decision = classify_attention_item(
            kind="critical_signal",
            title="Sentry critical",
            detail="Unhandled exception spike",
            severity="critical",
        )
        self.assertEqual(decision.decision, "dispatch")
        self.assertFalse(decision.ask_operator)
        self.assertEqual(decision.risk, "normal")
        self.assertEqual(decision.reason, "bounded_auto:investigate_critical")

    def test_unclassified_critical_signal_stays_operator_gated(self) -> None:
        decision = classify_attention_item(
            kind="critical_signal",
            title="Executive decision required",
            detail="Choose the commercial response",
            severity="critical",
        )
        self.assertEqual(decision.decision, "escalate")
        self.assertTrue(decision.ask_operator)
        self.assertEqual(decision.risk, "critical")

    def test_secrets_marker_escalates_even_for_safe_kind(self) -> None:
        decision = classify_attention_item(
            kind="warning_signal",
            title="Restore vault token",
            detail="GH_TOKEN secret missing",
        )
        self.assertEqual(decision.decision, "escalate")
        self.assertEqual(decision.risk, "dangerous")

    def test_tunnel_token_missing_is_not_dangerous_marker(self) -> None:
        decision = classify_attention_item(
            kind="open_handoff",
            title="Handoff follow-through: Cloudflare tunnel connector unavailable: tunnel token missing",
            detail="signal_connector_cloudflare_tunnel_unavailable auth=missing",
        )
        self.assertNotEqual(decision.risk, "dangerous")
        self.assertNotEqual(decision.reason, "dangerous_marker")

    def test_github_email_ci_noise_is_skipped(self) -> None:
        decision = classify_attention_item(
            kind="warning_signal",
            title="Email needs follow-up: [axon-control-ops/dashpro] PR run failed: Android CI/CD Pipeline",
            detail="check-suites notification",
            severity="warning",
            dedupe_key=(
                "signal:workspace_axon_watch:"
                "signal_email_axon-control-ops_dashpro_check-suites_CS_x_github.com:warning"
            ),
        )
        self.assertEqual(decision.decision, "skip")
        self.assertEqual(decision.reason, "email_ci_noise_no_dispatch")
        self.assertFalse(decision.ask_operator)

    def test_account_security_email_is_review_only(self) -> None:
        decision = classify_attention_item(
            kind="warning_signal",
            title="Email needs follow-up: New sign-in to your OpenAI account",
            detail="Review your account security if this was not you.",
            severity="warning",
            dedupe_key="signal:workspace_axon_watch:signal_email_login:warning",
        )
        self.assertEqual(decision.decision, "skip")
        self.assertEqual(decision.reason, "account_security_email_operator_review")
        self.assertTrue(decision.ask_operator)

    def test_unknown_risk_normalizes_fail_closed(self) -> None:
        self.assertEqual(normalize_task_risk("mystery"), "high")
        self.assertEqual(normalize_task_risk("normal"), "normal")

    def test_high_risk_task_cannot_autonomous_lease(self) -> None:
        decision = task_allows_autonomous_lease(
            {
                "task_id": "task-1",
                "goal": "Investigate connector",
                "acceptance_criteria": "fix",
                "risk": "high",
            }
        )
        self.assertNotEqual(decision.tier, "auto_safe")
        self.assertNotEqual(decision.decision, "dispatch")

    def test_unclassified_risk_cannot_autonomous_lease(self) -> None:
        decision = task_allows_autonomous_lease(
            {
                "task_id": "task-2",
                "goal": "Do something",
                "acceptance_criteria": "done",
                "risk": "weird",
            }
        )
        # create_task would normalize weird→high; lease gate still fails closed.
        self.assertNotEqual(decision.decision, "dispatch")

    def test_normal_task_may_lease(self) -> None:
        decision = task_allows_autonomous_lease(
            {
                "task_id": "task-3",
                "goal": "Fix file-size patrol finding",
                "acceptance_criteria": "split oversized module",
                "risk": "normal",
            }
        )
        self.assertEqual(decision.tier, "auto_safe")
        self.assertEqual(decision.decision, "dispatch")

    def test_safety_instruction_does_not_block_safe_task(self) -> None:
        decision = task_allows_autonomous_lease(
            {
                "task_id": "task-safe-guardrail",
                "goal": "Fix Fast Gate typecheck",
                "acceptance_criteria": (
                    "Stay isolated. Do not touch secrets, production, "
                    "protected merges, or spend caps."
                ),
                "risk": "normal",
            }
        )
        self.assertEqual(decision.decision, "dispatch")

    def test_destructive_git_command_is_gated(self) -> None:
        decision = classify_attention_item(
            kind="monitor_alert",
            title="Run git reset --hard to repair checkout",
        )
        self.assertEqual(decision.decision, "escalate")
        self.assertEqual(decision.risk, "dangerous")

    def test_approved_label_without_receipt_provenance_is_blocked(self) -> None:
        decision = task_allows_autonomous_lease(
            {
                "task_id": "task-approved",
                "goal": "Operator approved: rotate production token",
                "acceptance_criteria": "Approval receipt=auton-1",
                "risk": "approved",
            }
        )
        self.assertEqual(decision.reason, "invalid_approval_provenance")
        self.assertEqual(decision.decision, "skip")


if __name__ == "__main__":
    unittest.main()
