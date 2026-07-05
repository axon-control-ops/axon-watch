"""Tests for DashPro monitor slice inbox projection."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
for module_name in list(sys.modules):
    if module_name == "app" or module_name.startswith("app."):
        sys.modules.pop(module_name, None)
sys.path.insert(0, str(WATCH_SERVICE_ROOT))

from app.signals.monitor_signal import monitor_inbox_item, monitor_inbox_items  # noqa: E402


class DashProMonitorSignalTests(unittest.TestCase):
    def test_monitor_inbox_item_skips_ok_and_skipped(self) -> None:
        self.assertIsNone(
            monitor_inbox_item(
                {
                    "check_id": "dashpro_sentry_recent_issues",
                    "status": "ok",
                    "detail": "fine",
                }
            )
        )
        self.assertIsNone(
            monitor_inbox_item(
                {
                    "check_id": "dashpro_posthog_recent_events",
                    "status": "skipped",
                    "detail": "missing token",
                }
            )
        )

    def test_monitor_inbox_item_emits_warning_signal(self) -> None:
        item = monitor_inbox_item(
            {
                "check_id": "dashpro_sentry_recent_issues",
                "check_type": "sentry_recent_issues",
                "service": "Sentry",
                "workspace_id": "workspace_dashpro",
                "status": "warning",
                "detail": "3 unresolved issues",
            }
        )
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual("signal_monitor_dashpro_sentry_recent_issues_warning", item["signal_id"])
        self.assertEqual("high", item["severity"])
        self.assertEqual("dashpro_monitor", item["meta"]["signal_family"])

    def test_monitor_inbox_items_filters_ok(self) -> None:
        items = monitor_inbox_items(
            [
                {"check_id": "a", "status": "ok", "detail": "fine"},
                {
                    "check_id": "b",
                    "status": "critical",
                    "detail": "broken",
                    "service": "PostHog",
                },
            ]
        )
        self.assertEqual(1, len(items))
        self.assertEqual("critical", items[0]["severity"])


if __name__ == "__main__":
    unittest.main()
