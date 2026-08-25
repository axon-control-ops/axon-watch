from __future__ import annotations

import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_app_loader import prepare_control_plane_imports

prepare_control_plane_imports()

from app.cli_runtime.codex_usage_probe import (  # noqa: E402
    codex_usage_allows_agent_retry,
    probe_codex_usage,
    record_codex_usage_limit_hit,
    reset_codex_usage_limit_state_for_tests,
)


class CodexUsageProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_codex_usage_limit_state_for_tests()
        self.addCleanup(reset_codex_usage_limit_state_for_tests)

    def test_reads_local_log_activity_without_claiming_quota_percent(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            db = Path(tempdir) / "logs.sqlite"
            conn = sqlite3.connect(str(db))
            conn.execute(
                "CREATE TABLE logs (ts INTEGER NOT NULL, target TEXT NOT NULL, feedback_log_body TEXT, estimated_bytes INTEGER NOT NULL DEFAULT 0)"
            )
            conn.execute(
                "INSERT INTO logs (ts, target, feedback_log_body, estimated_bytes) VALUES (?, ?, ?, ?)",
                (
                    int(time.time()),
                    "codex_api::sse::responses",
                    "session_task.turn model=gpt-5.5",
                    1200,
                ),
            )
            conn.commit()
            conn.close()
            with patch.dict(
                "os.environ",
                {"AXON_WATCH_CODEX_LOGS_DB": str(db)},
                clear=False,
            ):
                usage = probe_codex_usage(force_refresh=True)
        self.assertTrue(usage["ok"])
        self.assertEqual("codex_local_logs", usage["source"])
        self.assertEqual(1, usage["events_24h"])
        self.assertEqual(1200, usage["estimated_bytes_24h"])
        self.assertIn("no live account-quota", usage["message"])

    def test_observed_limit_blocks_retry_until_reset(self) -> None:
        record_codex_usage_limit_hit("Codex CLI failed: ActionRequiredError: out of usage")
        usage = probe_codex_usage(force_refresh=True)
        self.assertTrue(usage["limit_reached"])
        self.assertFalse(codex_usage_allows_agent_retry(usage))


if __name__ == "__main__":
    unittest.main()
