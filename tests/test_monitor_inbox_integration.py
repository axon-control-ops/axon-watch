"""DashPro monitor probe failures → assembled watch inbox snapshot tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
_WATCH_PATH = str(WATCH_ROOT)

STABLE_CONNECTORS = [
    {
        "connector_id": "control_plane",
        "display_name": "Control plane",
        "status": "ok",
        "required": True,
    },
    {
        "connector_id": "console_web",
        "display_name": "Console web",
        "status": "ok",
        "required": True,
    },
]


class MonitorInboxIntegrationTests(unittest.TestCase):
    get_inbox_snapshot: object
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
        from app.signals.store import get_inbox_snapshot  # noqa: WPS433

        self.get_inbox_snapshot = get_inbox_snapshot

    def tearDown(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        while _WATCH_PATH in sys.path:
            sys.path.remove(_WATCH_PATH)
        sys.modules.update(self._saved_modules)

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records")
    def test_critical_monitor_appears_in_assembled_inbox(
        self, probe_monitors, _email, _acked
    ) -> None:
        probe_monitors.return_value = [
            {
                "check_id": "dashpro_sentry_recent_issues",
                "check_type": "sentry_recent_issues",
                "service": "Sentry",
                "workspace_id": "workspace_dashpro",
                "workspace_label": "DashPro",
                "status": "critical",
                "detail": "3 unresolved issue(s)",
            }
        ]
        payload = self.get_inbox_snapshot(connector_records=list(STABLE_CONNECTORS))
        signal_ids = [
            str(item.get("signal_id"))
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        self.assertIn("signal_monitor_dashpro_sentry_recent_issues_critical", signal_ids)
        self.assertNotIn("signal_watch_bootstrap_ready", signal_ids)
        monitor_items = [
            item
            for item in payload["items"]
            if str(item.get("source")) == "watch"
            and str((item.get("meta") or {}).get("signal_family")) == "child_project_monitor"
        ]
        self.assertEqual(1, len(monitor_items))
        self.assertEqual("critical", monitor_items[0]["severity"])
        self.assertEqual("investigate", monitor_items[0]["action_type"])

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records")
    def test_ok_and_skipped_monitors_stay_out_of_inbox(
        self, probe_monitors, _email, _acked
    ) -> None:
        probe_monitors.return_value = [
            {
                "check_id": "dashpro_posthog_recent_events",
                "service": "PostHog",
                "workspace_id": "workspace_dashpro",
                "status": "ok",
                "detail": "events flowing",
            },
            {
                "check_id": "dashpro_sentry_recent_issues",
                "service": "Sentry",
                "workspace_id": "workspace_dashpro",
                "status": "skipped",
                "detail": "auth not configured",
            },
        ]
        payload = self.get_inbox_snapshot(connector_records=list(STABLE_CONNECTORS))
        signal_ids = [
            str(item.get("signal_id"))
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        self.assertFalse(any(signal_id.startswith("signal_monitor_") for signal_id in signal_ids))

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records")
    def test_transport_failure_downranked_in_assembled_inbox(
        self, probe_monitors, _email, _acked
    ) -> None:
        probe_monitors.return_value = [
            {
                "check_id": "dashpro_posthog_recent_events",
                "check_type": "posthog_recent_events",
                "service": "PostHog",
                "workspace_id": "workspace_dashpro",
                "workspace_label": "DashPro",
                "status": "warning",
                "detail": "PostHog API query failed: timed out",
            }
        ]
        payload = self.get_inbox_snapshot(connector_records=list(STABLE_CONNECTORS))
        monitor_items = [
            item
            for item in payload["items"]
            if str(item.get("signal_id", "")).startswith("signal_monitor_")
        ]
        self.assertEqual(1, len(monitor_items))
        self.assertEqual("warning", monitor_items[0]["severity"])

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records")
    def test_threshold_warning_upranked_to_high_in_assembled_inbox(
        self, probe_monitors, _email, _acked
    ) -> None:
        probe_monitors.return_value = [
            {
                "check_id": "dashpro_sentry_recent_issues",
                "check_type": "sentry_recent_issues",
                "service": "Sentry",
                "workspace_id": "workspace_dashpro",
                "workspace_label": "DashPro",
                "status": "warning",
                "detail": "Sentry returned 12 unresolved issue(s), 48 event(s)",
            }
        ]
        payload = self.get_inbox_snapshot(connector_records=list(STABLE_CONNECTORS))
        monitor_items = [
            item
            for item in payload["items"]
            if str(item.get("signal_id", "")).startswith("signal_monitor_")
        ]
        self.assertEqual(1, len(monitor_items))
        self.assertEqual("high", monitor_items[0]["severity"])
        self.assertNotIn("signal_watch_bootstrap_ready", [i.get("signal_id") for i in payload["items"]])

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records")
    def test_posthog_zero_events_upranked_to_high_in_assembled_inbox(
        self, probe_monitors, _email, _acked
    ) -> None:
        probe_monitors.return_value = [
            {
                "check_id": "dashpro_posthog_recent_events",
                "check_type": "posthog_recent_events",
                "service": "PostHog",
                "workspace_id": "workspace_dashpro",
                "workspace_label": "DashPro",
                "status": "warning",
                "detail": "PostHog project is reachable but returned zero recent events",
            }
        ]
        payload = self.get_inbox_snapshot(connector_records=list(STABLE_CONNECTORS))
        monitor_items = [
            item
            for item in payload["items"]
            if str(item.get("signal_id", "")).startswith("signal_monitor_")
        ]
        self.assertEqual(1, len(monitor_items))
        self.assertEqual("high", monitor_items[0]["severity"])
        self.assertNotIn("signal_watch_bootstrap_ready", [i.get("signal_id") for i in payload["items"]])

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records")
    def test_posthog_auth_failure_appears_as_critical_in_assembled_inbox(
        self, probe_monitors, _email, _acked
    ) -> None:
        probe_monitors.return_value = [
            {
                "check_id": "dashpro_posthog_recent_events",
                "check_type": "posthog_recent_events",
                "service": "PostHog",
                "workspace_id": "workspace_dashpro",
                "workspace_label": "DashPro",
                "status": "critical",
                "detail": "PostHog API rejected the personal API key",
            }
        ]
        payload = self.get_inbox_snapshot(connector_records=list(STABLE_CONNECTORS))
        signal_ids = [
            str(item.get("signal_id"))
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        self.assertIn("signal_monitor_dashpro_posthog_recent_events_critical", signal_ids)
        self.assertNotIn("signal_watch_bootstrap_ready", signal_ids)
        monitor_items = [
            item
            for item in payload["items"]
            if str(item.get("signal_id", "")).startswith("signal_monitor_")
        ]
        self.assertEqual(1, len(monitor_items))
        self.assertEqual("critical", monitor_items[0]["severity"])
        self.assertEqual("investigate", monitor_items[0]["action_type"])

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records")
    def test_supabase_storage_critical_appears_in_assembled_inbox(
        self, probe_monitors, _email, _acked
    ) -> None:
        probe_monitors.return_value = [
            {
                "check_id": "dashpro_supabase_storage_quota",
                "check_type": "supabase_storage_quota",
                "service": "Supabase Storage",
                "workspace_id": "workspace_dashpro",
                "workspace_label": "DashPro",
                "status": "critical",
                "detail": (
                    "Supabase Storage 980 MB / 1.00 GB (98%). "
                    "Top buckets: tts-audio 980 MB (10 files)"
                ),
            }
        ]
        payload = self.get_inbox_snapshot(connector_records=list(STABLE_CONNECTORS))
        signal_ids = [
            str(item.get("signal_id"))
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        self.assertIn(
            "signal_monitor_dashpro_supabase_storage_quota_critical", signal_ids
        )
        self.assertNotIn("signal_watch_bootstrap_ready", signal_ids)
        monitor_items = [
            item
            for item in payload["items"]
            if str(item.get("signal_id", "")).startswith("signal_monitor_")
        ]
        self.assertEqual(1, len(monitor_items))
        self.assertEqual("critical", monitor_items[0]["severity"])
        self.assertEqual("investigate", monitor_items[0]["action_type"])

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records")
    def test_supabase_storage_threshold_warning_upranked_to_high_in_assembled_inbox(
        self, probe_monitors, _email, _acked
    ) -> None:
        probe_monitors.return_value = [
            {
                "check_id": "dashpro_supabase_storage_quota",
                "check_type": "supabase_storage_quota",
                "service": "Supabase Storage",
                "workspace_id": "workspace_dashpro",
                "workspace_label": "DashPro",
                "status": "warning",
                "detail": (
                    "Supabase Storage 850 MB / 1.00 GB (85%). "
                    "Top buckets: tts-audio 850 MB (10 files)"
                ),
            }
        ]
        payload = self.get_inbox_snapshot(connector_records=list(STABLE_CONNECTORS))
        monitor_items = [
            item
            for item in payload["items"]
            if str(item.get("signal_id", "")).startswith("signal_monitor_")
        ]
        self.assertEqual(1, len(monitor_items))
        self.assertEqual("high", monitor_items[0]["severity"])
        self.assertNotIn(
            "signal_watch_bootstrap_ready",
            [item.get("signal_id") for item in payload["items"]],
        )

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records")
    def test_sentry_issues_meta_preserved_in_assembled_inbox(
        self, probe_monitors, _email, _acked
    ) -> None:
        issues = [
            {
                "id": "123",
                "title": "TypeError: boom",
                "count": 4,
                "permalink": "https://sentry.io/issues/123/",
            }
        ]
        probe_monitors.return_value = [
            {
                "check_id": "dashpro_sentry_recent_issues",
                "check_type": "sentry_recent_issues",
                "service": "Sentry",
                "workspace_id": "workspace_dashpro",
                "workspace_label": "DashPro",
                "status": "critical",
                "detail": "1 unresolved issue(s)",
                "issues": issues,
            }
        ]
        payload = self.get_inbox_snapshot(connector_records=list(STABLE_CONNECTORS))
        monitor_items = [
            item
            for item in payload["items"]
            if str(item.get("signal_id", "")).startswith("signal_monitor_")
        ]
        self.assertEqual(1, len(monitor_items))
        meta = monitor_items[0].get("meta")
        self.assertIsInstance(meta, dict)
        assert isinstance(meta, dict)
        self.assertEqual(issues, meta.get("sentry_issues"))
        self.assertEqual(1, meta.get("sentry_issue_count"))


if __name__ == "__main__":
    unittest.main()
