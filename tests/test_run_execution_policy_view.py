"""A run's resolved authority must be readable as data, not guessed from a toggle."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.runs.execution_policy_view import (
    parse_execution_policy_summary,
    run_execution_policy,
)


class ParseExecutionPolicySummaryTests(unittest.TestCase):
    def test_full_access_with_scoped_writes(self) -> None:
        parsed = parse_execution_policy_summary(
            "policy-abc access=full writes=website,docs network=none timeout=1200s"
        )
        self.assertEqual(parsed["execution_access"], "full")
        self.assertEqual(parsed["write_paths"], ["website", "docs"])
        self.assertFalse(parsed["read_only"])

    def test_read_only_marker_becomes_empty_scope(self) -> None:
        parsed = parse_execution_policy_summary(
            "policy-abc access=consultative writes=read-only network=none timeout=1200s"
        )
        self.assertEqual(parsed["write_paths"], [])
        self.assertTrue(parsed["read_only"])

    def test_unrelated_summary_is_not_a_policy(self) -> None:
        self.assertIsNone(parse_execution_policy_summary("Run completed"))


class RunExecutionPolicyTests(unittest.TestCase):
    def _history(self, *summaries: str) -> dict:
        return {
            "items": [
                {"receipt": {"type": "agent_execution_policy", "summary": s}} for s in summaries
            ]
        }

    def test_latest_policy_wins(self) -> None:
        with patch(
            "app.runs.service.get_run_history",
            return_value=self._history(
                "policy-1 access=consultative writes=read-only network=none",
                "policy-2 access=full writes=website network=none",
            ),
        ):
            result = run_execution_policy("run_x")
        self.assertTrue(result["known"])
        self.assertEqual(result["write_paths"], ["website"])

    def test_unknown_is_explicit_and_not_full(self) -> None:
        # A queued run has resolved nothing yet. Defaulting to "full" here is
        # exactly how the dock came to claim FULL ACCESS on read-only threads.
        with patch("app.runs.service.get_run_history", return_value={"items": []}):
            result = run_execution_policy("run_x")
        self.assertFalse(result["known"])
        self.assertEqual(result["execution_access"], "unknown")
        self.assertNotEqual(result["execution_access"], "full")


if __name__ == "__main__":
    unittest.main()
