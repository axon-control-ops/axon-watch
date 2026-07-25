"""Tests for DashPro monitor slice inbox projection."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
_WATCH_PATH = str(WATCH_SERVICE_ROOT)


class DashProMonitorSignalTests(unittest.TestCase):
    monitor_signal: object
    _saved_modules: dict[str, object]

    def setUp(self) -> None:
        self._saved_modules = {
            name: module
            for name, module in sys.modules.items()
            if name == "app" or name.startswith("app.")
        }
        for name in self._saved_modules:
            del sys.modules[name]
        while _WATCH_PATH in sys.path:
            sys.path.remove(_WATCH_PATH)
        sys.path.insert(0, _WATCH_PATH)
        import app.signals.monitor_signal as monitor_signal  # noqa: WPS433

        self.monitor_signal = monitor_signal

    def tearDown(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        while _WATCH_PATH in sys.path:
            sys.path.remove(_WATCH_PATH)
        sys.modules.update(self._saved_modules)

    def test_monitor_inbox_item_skips_ok_and_skipped(self) -> None:
        self.assertIsNone(
            self.monitor_signal.monitor_inbox_item(
                {
                    "check_id": "dashpro_sentry_recent_issues",
                    "status": "ok",
                    "detail": "fine",
                }
            )
        )
        self.assertIsNone(
            self.monitor_signal.monitor_inbox_item(
                {
                    "check_id": "dashpro_posthog_recent_events",
                    "status": "skipped",
                    "detail": "missing token",
                }
            )
        )

    def test_monitor_inbox_item_emits_warning_signal(self) -> None:
        item = self.monitor_signal.monitor_inbox_item(
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
        self.assertEqual("child_project_monitor", item["meta"]["signal_family"])

    def test_monitor_inbox_item_downranks_transport_warning(self) -> None:
        item = self.monitor_signal.monitor_inbox_item(
            {
                "check_id": "dashpro_posthog_recent_events",
                "check_type": "posthog_recent_events",
                "service": "PostHog",
                "workspace_id": "workspace_dashpro",
                "status": "warning",
                "detail": "PostHog API query failed: The read operation timed out",
            }
        )
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual("warning", item["severity"])

    def test_monitor_inbox_item_attaches_sentry_issues(self) -> None:
        issues = [
            {
                "id": "12345",
                "short_id": "RN-1",
                "title": "TypeError: boom",
                "level": "error",
                "count": 4,
                "permalink": "https://sentry.io/issues/12345/",
                "culprit": "app.js",
            }
        ]
        item = self.monitor_signal.monitor_inbox_item(
            {
                "check_id": "dashpro_sentry_recent_issues",
                "check_type": "sentry_recent_issues",
                "service": "Sentry",
                "workspace_id": "workspace_dashpro",
                "status": "critical",
                "detail": "unresolved issues",
                "issues": issues,
            }
        )
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(issues, item["meta"]["sentry_issues"])
        self.assertEqual(1, item["meta"]["sentry_issue_count"])

    def test_monitor_inbox_items_filters_ok(self) -> None:
        items = self.monitor_signal.monitor_inbox_items(
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
