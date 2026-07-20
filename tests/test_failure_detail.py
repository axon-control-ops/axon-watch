"""Failure detail normalization for roster and scheduler."""

from __future__ import annotations

import unittest

import sys
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.failure_detail import (  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
