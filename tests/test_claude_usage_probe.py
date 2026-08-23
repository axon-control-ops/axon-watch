from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.claude_usage_probe import (  # noqa: E402
    claude_usage_allows_agent_retry,
    probe_claude_usage,
    record_claude_usage_limit_hit,
    reset_claude_usage_limit_state_for_tests,
)

_SAMPLE_STATS = {
    "dailyActivity": [
        {"date": "2026-04-29", "messageCount": 49, "sessionCount": 3, "toolCallCount": 58},
        {"date": "2026-04-30", "messageCount": 144, "sessionCount": 3, "toolCallCount": 73},
    ],
    "dailyModelTokens": [
        {"date": "2026-04-29", "tokensByModel": {"claude-sonnet-4-6": 38089, "claude-haiku-4-5-20251001": 23530}},
        {"date": "2026-04-30", "tokensByModel": {"claude-sonnet-4-6": 72208, "claude-haiku-4-5-20251001": 8743}},
    ],
    "modelUsage": {
        "claude-sonnet-4-6": {
            "inputTokens": 1_000_000,
            "outputTokens": 500_000,
            "cacheReadInputTokens": 2_000_000,
            "cacheCreationInputTokens": 100_000,
        },
    },
    "totalSessions": 106,
    "totalMessages": 22179,
}

_MISSING_STATS_CACHE = "/nonexistent/stats-cache.json"


class ClaudeUsageProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_claude_usage_limit_state_for_tests()
        patch.dict(
            "app.cli_runtime.claude_usage_probe._USAGE_CACHE",
            {"fetched_at": 0.0, "payload": None},
        ).start()
        self.addCleanup(patch.stopall)
        self.addCleanup(reset_claude_usage_limit_state_for_tests)

    def test_probe_reads_local_stats_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            stats_path = Path(tmp_dir) / "stats-cache.json"
            stats_path.write_text(json.dumps(_SAMPLE_STATS), encoding="utf-8")
            with patch.dict("os.environ", {"AXON_WATCH_CLAUDE_STATS_CACHE": str(stats_path)}):
                usage = probe_claude_usage(force_refresh=True)

        self.assertTrue(usage["ok"])
        self.assertEqual(usage["most_recent_day"]["date"], "2026-04-30")
        self.assertEqual(usage["tokens_7d"], 38089 + 23530 + 72208 + 8743)
        self.assertEqual(usage["total_sessions"], 106)
        self.assertGreater(usage["lifetime_estimated_cost_usd"], 0)
        self.assertFalse(usage["limit_reached"])
        self.assertTrue(usage["allows_agent_retry"])

    def test_probe_unavailable_when_no_stats_cache(self) -> None:
        with patch.dict("os.environ", {"AXON_WATCH_CLAUDE_STATS_CACHE": _MISSING_STATS_CACHE}):
            usage = probe_claude_usage(force_refresh=True)
        self.assertFalse(usage["ok"])
        self.assertTrue(usage["allows_agent_retry"])

    def test_limit_hit_blocks_retry_until_reset(self) -> None:
        future_epoch = int(time.time()) + 3600
        record_claude_usage_limit_hit(f"Claude AI usage limit reached|{future_epoch}")
        with patch.dict("os.environ", {"AXON_WATCH_CLAUDE_STATS_CACHE": _MISSING_STATS_CACHE}):
            usage = probe_claude_usage(force_refresh=True)
        self.assertTrue(usage["limit_reached"])
        self.assertFalse(usage["allows_agent_retry"])
        self.assertFalse(claude_usage_allows_agent_retry(usage))
        self.assertIn("Resets around", usage["limit_reset_hint"])

    def test_limit_hit_expires_after_reset_epoch(self) -> None:
        past_epoch = int(time.time()) - 10
        record_claude_usage_limit_hit(f"Claude AI usage limit reached|{past_epoch}")
        with patch.dict("os.environ", {"AXON_WATCH_CLAUDE_STATS_CACHE": _MISSING_STATS_CACHE}):
            usage = probe_claude_usage(force_refresh=True)
        self.assertFalse(usage["limit_reached"])
        self.assertTrue(usage["allows_agent_retry"])

    def test_allows_retry_defaults_true_for_missing_or_non_dict_usage(self) -> None:
        self.assertTrue(claude_usage_allows_agent_retry(None))
        self.assertTrue(claude_usage_allows_agent_retry({}))


if __name__ == "__main__":
    unittest.main()
