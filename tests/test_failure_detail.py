"""Failure detail normalization for roster and scheduler."""

from __future__ import annotations

import unittest

import sys
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.failure_detail import (  # noqa: E402
    is_agent_session_interrupted_failure,
    is_billing_block_failure,
    is_operator_stopped_failure,
    is_restart_interrupted_failure,
    is_runtime_auth_failure,
    is_shift_continuation_failure,
    is_usage_limit_failure,
    normalize_operator_failure_detail,
)


class FailureDetailTests(unittest.TestCase):
    def test_normalize_strips_lane_b_fallback_wrapper(self) -> None:
        wrapped = (
            "Lane B agent fallback reply generated "
            "(CLI runtime timed out after 240s.; Cursor Cloud Agent unavailable)"
        )
        self.assertEqual(
            "CLI runtime timed out after 240s.",
            normalize_operator_failure_detail(wrapped),
        )

    def test_normalize_strips_dispatch_prefix(self) -> None:
        self.assertEqual(
            "cursor agent unavailable",
            normalize_operator_failure_detail(
                "continuous worker dispatch failed: cursor agent unavailable",
            ),
        )

    def test_usage_limit_preferred_over_unavailable_peers(self) -> None:
        wrapped = (
            "Lane B agent fallback reply generated "
            "(Codex CLI (local) unavailable; Running as unit: axon-agent.scope; "
            "Invocation ID: abc; ActionRequiredError: You're out of usage.)"
        )
        normalized = normalize_operator_failure_detail(wrapped)
        self.assertIn("ActionRequiredError", normalized)
        self.assertNotIn("Codex CLI (local) unavailable", normalized)
        self.assertTrue(is_usage_limit_failure(wrapped))

    def test_usage_limit_detected_after_normalization(self) -> None:
        wrapped = (
            "Lane B agent fallback reply generated "
            "(ActionRequiredError: Increase limits for faster responses You're out of usage.)"
        )
        self.assertTrue(is_usage_limit_failure(wrapped))
        self.assertFalse(is_usage_limit_failure("verify:contracts — assertion failed"))
        self.assertFalse(is_usage_limit_failure("ActionRequiredError"))
        self.assertFalse(is_usage_limit_failure("ActionRequiredError: Please accept the terms"))
        self.assertTrue(is_usage_limit_failure("ActionRequiredError: You're out of usage."))

    def test_billing_block_unpaid_invoice_detected(self) -> None:
        wrapped = (
            "Lane B agent fallback reply generated "
            "(Running as unit: axon-agent-6e26fd5057.scope; invocation ID: "
            "59f73eb8b8f1487aa9455bf5c83bac00\n"
            "ActionRequiredError: You have an unpaid invoice Visit "
            "[cursor.com/dashboard](https://cursor.com/dashboard) and pay your "
            "invoice in Stripe to resume requests.)"
        )
        self.assertTrue(is_billing_block_failure(wrapped))
        self.assertFalse(is_usage_limit_failure(wrapped))
        self.assertFalse(is_runtime_auth_failure(wrapped))
        self.assertFalse(is_billing_block_failure("ActionRequiredError: Please accept the terms"))
        self.assertFalse(is_billing_block_failure("verify:contracts — assertion failed"))
        normalized = normalize_operator_failure_detail(wrapped)
        self.assertIn("unpaid invoice", normalized.lower())
        self.assertNotIn("Running as unit", normalized)

    def test_runtime_auth_detected_after_normalization(self) -> None:
        wrapped = (
            "Lane B agent fallback reply generated "
            "(Cursor is installed but not signed in. Run `cursor agent login` or unlock /vault.; "
            "Cursor Cloud Agent unavailable)"
        )
        self.assertTrue(is_runtime_auth_failure(wrapped))
        self.assertFalse(is_runtime_auth_failure("verify:contracts — assertion failed"))

    def test_auth_probe_timeout_is_runtime_auth(self) -> None:
        wrapped = (
            "Lane B agent fallback reply generated "
            "(Cursor auth probe timed out. Run `cursor agent status` manually.; "
            "Cursor Cloud Agent unavailable)"
        )
        self.assertTrue(is_runtime_auth_failure(wrapped))
        self.assertEqual(
            "Cursor auth probe timed out. Run `cursor agent status` manually.",
            normalize_operator_failure_detail(wrapped),
        )

    def test_session_interrupted_detected_for_sigterm(self) -> None:
        wrapped = (
            "Lane B agent fallback reply generated "
            "(Cursor CLI exited with status 143.; Cursor Cloud Agent unavailable)"
        )
        self.assertTrue(is_agent_session_interrupted_failure(wrapped))
        self.assertTrue(is_shift_continuation_failure(wrapped))
        self.assertEqual(
            "Cursor CLI exited with status 143.",
            normalize_operator_failure_detail(wrapped),
        )

    def test_session_interrupted_detected_for_oom(self) -> None:
        self.assertTrue(is_agent_session_interrupted_failure("Process exited with status 137"))
        self.assertTrue(is_agent_session_interrupted_failure("Process killed by oom-kill"))

    def test_operator_stop_is_shift_continuation(self) -> None:
        detail = "Runtime execution stopped by operator before the CLI finished."
        self.assertTrue(is_operator_stopped_failure(detail))
        self.assertTrue(is_shift_continuation_failure(detail))
        wrapped = (
            "Lane B agent fallback reply generated "
            f"({detail}; Cursor Cloud Agent unavailable)"
        )
        self.assertTrue(is_operator_stopped_failure(wrapped))
        self.assertTrue(is_shift_continuation_failure(wrapped))
        self.assertFalse(is_agent_session_interrupted_failure(detail))

    def test_restart_interrupt_is_shift_continuation(self) -> None:
        detail = "Run interrupted by control-plane restart"
        self.assertTrue(is_restart_interrupted_failure(detail))
        self.assertTrue(is_shift_continuation_failure(detail))
        self.assertFalse(is_agent_session_interrupted_failure(detail))

    def test_employee_restart_dispatch_is_shift_continuation(self) -> None:
        detail = "Continuous worker dispatch lost on control-plane restart"
        self.assertTrue(is_restart_interrupted_failure(detail))
        self.assertTrue(is_shift_continuation_failure(detail))


if __name__ == "__main__":
    unittest.main()
