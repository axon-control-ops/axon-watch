"""Lead-failure classifier: the root-cause fix for premature Ask cards.

Regression coverage for the exact bug reported: a Lead's failed shift was
unconditionally escalated with no diagnosis, and the frontend turned it into
a 4-option "how should the Lead handle this?" menu even for a single missing
requirement (workspace delivery not configured) with no real business choice.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.lead_failure_diagnosis import (  # noqa: E402
    MAX_AUTO_RECOVERY_ATTEMPTS,
    diagnose_lead_failure,
)


class _AssumeDeliveryConfiguredTestCase(unittest.TestCase):
    """Every test outside WorkspaceDeliveryConfigTests targets a step that
    only runs *after* the delivery-config check (step 3). Without pinning
    that check to "configured", any workspace_id with no real delivery
    policy in the store (true of every test fixture id) would hit step 3
    first regardless of what each test's `detail` actually says — silently
    testing the wrong branch. This is exactly what happened before this
    fixture existed: test_operator_sensitive_text_is_blocked and
    test_unclassified_failure_is_routed_automatically_not_asked both
    (mis)passed/failed via the delivery-config path, not the code they
    named.
    """

    def setUp(self) -> None:
        patcher = patch(
            "app.workspace_agents.lead_failure_diagnosis._workspace_delivery_configured",
            return_value=True,
        )
        patcher.start()
        self.addCleanup(patcher.stop)


class TransientFailureTests(_AssumeDeliveryConfiguredTestCase):
    def test_restart_interruption_is_auto_retried_without_asking(self) -> None:
        decision = diagnose_lead_failure(
            workspace_id="workspace_demo",
            run_id="run_abc",
            detail="Run interrupted by control-plane restart",
        )
        self.assertEqual("working", decision.card_type)
        self.assertFalse(decision.operator_action_required)
        self.assertTrue(decision.retry_eligible)
        self.assertEqual((), decision.choices)

    def test_exhausted_retries_produce_a_failed_card_not_a_loop(self) -> None:
        decision = diagnose_lead_failure(
            workspace_id="workspace_demo",
            run_id="run_abc",
            detail="Run interrupted by control-plane restart",
            prior_attempts=MAX_AUTO_RECOVERY_ATTEMPTS,
        )
        self.assertEqual("failed", decision.card_type)
        self.assertTrue(decision.operator_action_required)
        self.assertFalse(decision.retry_eligible)
        self.assertEqual((), decision.choices)


class OperatorGateFailureTests(_AssumeDeliveryConfiguredTestCase):
    def test_usage_limit_is_blocked_not_decision_required(self) -> None:
        decision = diagnose_lead_failure(
            workspace_id="workspace_demo",
            run_id="run_abc",
            detail="ActionRequiredError: You're out of usage. Increase limits to continue.",
        )
        self.assertEqual("blocked", decision.card_type)
        self.assertEqual("usage_limit", decision.classification)
        self.assertTrue(decision.operator_action_required)
        self.assertEqual((), decision.choices)  # no invented menu

    def test_billing_hold_is_blocked(self) -> None:
        decision = diagnose_lead_failure(
            workspace_id="workspace_demo",
            run_id="run_abc",
            detail="Billing: unpaid invoice is blocking this account",
        )
        self.assertEqual("blocked", decision.card_type)
        self.assertEqual("billing_block", decision.classification)
        self.assertTrue(decision.operator_action_required)

    def test_runtime_auth_is_blocked(self) -> None:
        decision = diagnose_lead_failure(
            workspace_id="workspace_demo",
            run_id="run_abc",
            detail="Cursor CLI is not signed in",
        )
        self.assertEqual("blocked", decision.card_type)
        self.assertEqual("runtime_auth", decision.classification)
        self.assertTrue(decision.operator_action_required)


class WorkspaceDeliveryConfigTests(unittest.TestCase):
    """The concrete reported example: MoveIT / workspace delivery not configured."""

    def test_missing_delivery_config_is_blocked_with_no_invented_menu(self) -> None:
        with patch(
            "app.workspace_agents.lead_failure_diagnosis._workspace_delivery_configured",
            return_value=False,
        ):
            decision = diagnose_lead_failure(
                workspace_id="workspace_moveit",
                run_id="run_eb27cfd30ee4",
                detail="Workspace delivery blocked: workspace delivery is not configured for MoveIT",
            )
        self.assertEqual("blocked", decision.card_type)
        self.assertEqual("missing_workspace_delivery_config", decision.classification)
        self.assertTrue(decision.operator_action_required)
        # The whole point of the fix: no "Fix / Inspect / Recovery Center / Hold"
        # menu for a single missing requirement.
        self.assertEqual((), decision.choices)
        self.assertIn("workspace_moveit", decision.recommended_action)
        self.assertTrue(decision.evidence)
        self.assertEqual("run_eb27cfd30ee4", decision.evidence[0].ref)

    def test_configured_delivery_does_not_match_this_class(self) -> None:
        """If delivery IS configured, this specific diagnosis must not fire —
        the real cause is something else and falls through to routing."""
        with patch(
            "app.workspace_agents.lead_failure_diagnosis._workspace_delivery_configured",
            return_value=True,
        ):
            decision = diagnose_lead_failure(
                workspace_id="workspace_moveit",
                run_id="run_abc",
                detail="Some other, unrelated failure text",
            )
        self.assertNotEqual("missing_workspace_delivery_config", decision.classification)

    def test_diagnosis_probe_failure_does_not_falsely_claim_a_config_problem(self) -> None:
        """A crash while checking live config must not be misread as 'confirmed broken'.

        _workspace_delivery_configured imports get_workspace_delivery_policy
        locally (inside the function), so the patch target is the source
        module, not a name imported into lead_failure_diagnosis's namespace.
        """
        from app.workspace_agents.lead_failure_diagnosis import _workspace_delivery_configured

        with patch(
            "app.workspace_delivery.config.get_workspace_delivery_policy",
            side_effect=RuntimeError("boom"),
        ):
            self.assertTrue(_workspace_delivery_configured("workspace_moveit"))


class UnsafeAndFallthroughTests(_AssumeDeliveryConfiguredTestCase):
    def test_operator_sensitive_text_is_blocked(self) -> None:
        decision = diagnose_lead_failure(
            workspace_id="workspace_demo",
            run_id="run_abc",
            detail="Refusing to push to production without explicit approval",
        )
        self.assertEqual("blocked", decision.card_type)
        self.assertEqual("operator_sensitive", decision.classification)
        self.assertTrue(decision.operator_action_required)

    def test_unclassified_failure_is_routed_automatically_not_asked(self) -> None:
        decision = diagnose_lead_failure(
            workspace_id="workspace_demo",
            run_id="run_abc",
            detail="TypeError: cannot read property of undefined in dashboard.tsx",
        )
        self.assertEqual("working", decision.card_type)
        self.assertEqual("unclassified_routable", decision.classification)
        self.assertFalse(decision.operator_action_required)
        self.assertEqual((), decision.choices)
        self.assertTrue(decision.recovery_eligible)


if __name__ == "__main__":
    unittest.main()
