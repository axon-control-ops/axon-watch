"""Failure detail normalization for roster and scheduler."""

from __future__ import annotations

import unittest

import sys
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.failure_detail import (  # noqa: E402
    is_agent_session_interrupted_failure,
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

    def test_usage_limit_detected_after_normalization(self) -> None:
        wrapped = (
            "Lane B agent fallback reply generated "
            "(ActionRequiredError: Increase limits for faster responses You're out of usage.)"
        )
        self.assertTrue(is_usage_limit_failure(wrapped))
        self.assertFalse(is_usage_limit_failure("verify:contracts — assertion failed"))

    def test_runtime_auth_detected_after_normalization(self) -> None:
        wrapped = (
            "Lane B agent fallback reply generated "
            "(Cursor is installed but not signed in. Run `cursor agent login` or unlock /vault.; "
            "Cursor Cloud Agent unavailable)"
        )
        self.assertTrue(is_runtime_auth_failure(wrapped))
        self.assertFalse(is_runtime_auth_failure("verify:contracts — assertion failed"))

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
