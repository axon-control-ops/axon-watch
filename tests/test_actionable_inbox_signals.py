"""Watch-side actionable inbox filtering tests (OP-B4)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
sys.path.insert(0, str(WATCH_ROOT))

from app.signals.inbox_filters import (  # noqa: E402
    should_emit_bootstrap_signal,
    summarize_actionable_inbox,
)
from app.signals.store import get_inbox_snapshot  # noqa: E402

MONITOR_ITEM = {
    "signal_id": "signal_monitor_dashpro_sentry_recent_issues_critical",
    "workspace_id": "workspace_dashpro",
    "title": "DashPro Sentry critical",
    "summary": "3 unresolved issues",
    "severity": "critical",
    "status": "open",
    "meta": {"signal_family": "child_project_monitor", "check_id": "dashpro_sentry_recent_issues"},
}

BOOTSTRAP_ITEM = {
    "signal_id": "signal_watch_bootstrap_ready",
    "title": "Watch bootstrap ready",
    "severity": "info",
    "status": "open",
}


class WatchInboxFilterTests(unittest.TestCase):
    def test_bootstrap_excluded_from_actionable_counts(self) -> None:
        summary = summarize_actionable_inbox([BOOTSTRAP_ITEM, MONITOR_ITEM])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(1, summary["critical_count"])
        self.assertEqual(MONITOR_ITEM, summary["top_items"][0])

    def test_bootstrap_only_inbox_has_zero_actionable_open_count(self) -> None:
        summary = summarize_actionable_inbox([BOOTSTRAP_ITEM])
        self.assertEqual(0, summary["open_count"])
        self.assertEqual([], summary["top_items"])

    def test_should_emit_bootstrap_only_without_live_monitor_items(self) -> None:
        self.assertTrue(should_emit_bootstrap_signal([]))
        self.assertFalse(should_emit_bootstrap_signal([MONITOR_ITEM]))

    @patch("app.signals.store.probe_monitor_records")
    def test_inbox_omits_bootstrap_when_monitor_signal_present(self, probe_monitors) -> None:
        probe_monitors.return_value = [
            {
                "check_id": "dashpro_sentry_recent_issues",
                "check_type": "sentry_recent_issues",
                "service": "Sentry",
                "workspace_id": "workspace_dashpro",
                "workspace_label": "DashPro",
                "status": "critical",
                "detail": "3 unresolved issues",
            }
        ]
        payload = get_inbox_snapshot(connector_records=[])
        signal_ids = [
            str(item.get("signal_id"))
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        self.assertIn("signal_monitor_dashpro_sentry_recent_issues_critical", signal_ids)
        self.assertNotIn("signal_watch_bootstrap_ready", signal_ids)


if __name__ == "__main__":
    unittest.main()
