"""Cursor usage-limit failures must stop the auto-start retry loop.

Regression: control-plane logs showed 18 identical
``RuntimeError: ActionRequiredError: ... You're out of usage.`` dispatch
failures inside two hours for family=cursor. Claude and Codex cache an
observed limit hit; Cursor did not, and cursor_usage_allows_agent_retry
deliberately fails open when the live pool cannot be read -- so every
scheduler tick reopened the gate and redispatched the same doomed shift.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.cursor_usage_probe import (  # noqa: E402
    cursor_usage_allows_agent_retry,
    cursor_usage_limit_hit_is_fresh,
    record_cursor_usage_limit_hit,
    reset_cursor_usage_limit_state_for_tests,
)

OUT_OF_USAGE = (
    "ActionRequiredError: Increase limits for faster responses You're out of "
    "usage. Switch to Auto, or ask your admin to increase your limit to continue."
)


class CursorUsageLimitBreakerTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_cursor_usage_limit_state_for_tests()
        self.addCleanup(reset_cursor_usage_limit_state_for_tests)

    def test_unreadable_pool_still_fails_open_without_an_observed_hit(self) -> None:
        """Unchanged contract: never invent an account-wide stop from nothing."""
        self.assertTrue(cursor_usage_allows_agent_retry(None))
        self.assertTrue(cursor_usage_allows_agent_retry({"ok": False}))

    def test_unreadable_pool_holds_the_gate_after_an_observed_hit(self) -> None:
        record_cursor_usage_limit_hit(OUT_OF_USAGE)
        self.assertTrue(cursor_usage_limit_hit_is_fresh())
        self.assertFalse(cursor_usage_allows_agent_retry(None))
        self.assertFalse(cursor_usage_allows_agent_retry({"ok": False}))

    def test_live_headroom_still_wins_over_a_cached_hit(self) -> None:
        """A readable pool with real headroom must still allow the retry."""
        record_cursor_usage_limit_hit(OUT_OF_USAGE)
        self.assertTrue(
            cursor_usage_allows_agent_retry(
                {"ok": True, "auto_percent_used": 10.0, "total_percent_used": 10.0}
            )
        )

    def test_exhausted_live_pool_still_blocks(self) -> None:
        self.assertFalse(
            cursor_usage_allows_agent_retry(
                {
                    "ok": True,
                    "on_demand_enabled": False,
                    "auto_percent_used": 100.0,
                    "total_percent_used": 100.0,
                }
            )
        )

    def test_reset_clears_the_breaker(self) -> None:
        record_cursor_usage_limit_hit(OUT_OF_USAGE)
        reset_cursor_usage_limit_state_for_tests()
        self.assertFalse(cursor_usage_limit_hit_is_fresh())
        self.assertTrue(cursor_usage_allows_agent_retry({"ok": False}))


if __name__ == "__main__":
    unittest.main()
