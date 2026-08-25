"""Watch-side actionable inbox filtering tests (OP-B4)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
_WATCH_PATH = str(WATCH_ROOT)

MONITOR_ITEM = {
    "signal_id": "signal_monitor_dashpro_sentry_recent_issues_critical",
    "workspace_id": "workspace_dashpro",
    "title": "DashPro Sentry critical",
    "summary": "3 unresolved issues",
    "severity": "critical",
    "status": "open",
    "meta": {"signal_family": "child_project_monitor", "check_id": "dashpro_sentry_recent_issues"},
}

CONNECTOR_ITEM = {
    "signal_id": "signal_connector_console_web_unavailable",
    "workspace_id": "workspace_axon_watch",
    "title": "Console web connector unavailable",
    "summary": "status=503",
    "severity": "critical",
    "status": "open",
    "source": "connector",
}

EMAIL_ITEM = {
    "signal_id": "signal_email_stub_invoice",
    "workspace_id": "workspace_axon_watch",
    "title": "Email needs follow-up: Microsoft invoice",
    "summary": "Review the invoice before the due date.",
    "severity": "high",
    "status": "open",
    "source": "email",
    "meta": {"signal_family": "email_triage"},
}

BOOTSTRAP_ITEM = {
    "signal_id": "signal_watch_bootstrap_ready",
    "title": "Watch bootstrap ready",
    "severity": "info",
    "status": "open",
}

SUMMARY_DEGRADED_ITEM = {
    "signal_id": "signal_runtime_summary_degraded",
    "title": "Bootstrap: runtime summary stale",
    "severity": "high",
    "status": "open",
}


class WatchInboxFilterTests(unittest.TestCase):
    inbox_filters: object
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
        from app.signals import inbox_filters  # noqa: WPS433
        from app.signals.store import get_inbox_snapshot  # noqa: WPS433

        self.inbox_filters = inbox_filters
        self.get_inbox_snapshot = get_inbox_snapshot

    def tearDown(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        while _WATCH_PATH in sys.path:
            sys.path.remove(_WATCH_PATH)
        sys.modules.update(self._saved_modules)

    def test_bootstrap_excluded_from_actionable_counts(self) -> None:
        summary = self.inbox_filters.summarize_actionable_inbox([BOOTSTRAP_ITEM, MONITOR_ITEM])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(1, summary["critical_count"])
        self.assertEqual(MONITOR_ITEM, summary["top_items"][0])

    def test_summary_degraded_excluded_when_connector_signal_present(self) -> None:
        summary = self.inbox_filters.summarize_actionable_inbox(
            [CONNECTOR_ITEM, SUMMARY_DEGRADED_ITEM]
        )
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(1, summary["critical_count"])
        self.assertEqual(0, summary["high_count"])
        self.assertEqual(CONNECTOR_ITEM, summary["top_items"][0])

    def test_bootstrap_only_inbox_has_zero_actionable_open_count(self) -> None:
        summary = self.inbox_filters.summarize_actionable_inbox([BOOTSTRAP_ITEM])
        self.assertEqual(0, summary["open_count"])
        self.assertEqual([], summary["top_items"])

    def test_should_emit_bootstrap_only_without_live_monitor_items(self) -> None:
        self.assertTrue(self.inbox_filters.should_emit_bootstrap_signal([]))
        self.assertFalse(self.inbox_filters.should_emit_bootstrap_signal([MONITOR_ITEM]))

    def test_should_emit_bootstrap_false_when_connector_items_present(self) -> None:
        self.assertFalse(
            self.inbox_filters.should_emit_bootstrap_signal([], [CONNECTOR_ITEM])
        )

    def test_should_emit_bootstrap_false_when_email_items_present(self) -> None:
        self.assertFalse(
            self.inbox_filters.should_emit_bootstrap_signal([], None, [EMAIL_ITEM])
        )

    def test_transport_warning_monitor_counts_as_actionable_not_critical(self) -> None:
        warning_item = {
            "signal_id": "signal_monitor_dashpro_posthog_recent_events_warning",
            "severity": "warning",
            "status": "open",
            "meta": {"signal_family": "child_project_monitor"},
        }
        summary = self.inbox_filters.summarize_actionable_inbox([warning_item])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(0, summary["high_count"])

    def test_threshold_warning_monitor_counts_as_high_not_critical(self) -> None:
        high_item = {
            "signal_id": "signal_monitor_dashpro_sentry_recent_issues_warning",
            "severity": "high",
            "status": "open",
            "meta": {"signal_family": "child_project_monitor"},
        }
        summary = self.inbox_filters.summarize_actionable_inbox([high_item])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])

    def test_posthog_threshold_warning_counts_as_high_not_critical(self) -> None:
        high_item = {
            "signal_id": "signal_monitor_dashpro_posthog_recent_events_warning",
            "severity": "high",
            "status": "open",
            "meta": {"signal_family": "child_project_monitor"},
        }
        summary = self.inbox_filters.summarize_actionable_inbox([high_item])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])

    def test_posthog_critical_counts_as_critical(self) -> None:
        critical_item = {
            "signal_id": "signal_monitor_dashpro_posthog_recent_events_critical",
            "severity": "critical",
            "status": "open",
            "meta": {"signal_family": "child_project_monitor"},
        }
        summary = self.inbox_filters.summarize_actionable_inbox([critical_item])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(1, summary["critical_count"])
        self.assertEqual(0, summary["high_count"])
        self.assertEqual(critical_item, summary["top_items"][0])

    def test_supabase_storage_critical_counts_as_critical(self) -> None:
        critical_item = {
            "signal_id": "signal_monitor_dashpro_supabase_storage_quota_critical",
            "severity": "critical",
            "status": "open",
            "meta": {"signal_family": "child_project_monitor"},
        }
        summary = self.inbox_filters.summarize_actionable_inbox([critical_item])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(1, summary["critical_count"])
        self.assertEqual(0, summary["high_count"])
        self.assertEqual(critical_item, summary["top_items"][0])

    def test_supabase_storage_threshold_warning_counts_as_high_not_critical(self) -> None:
        high_item = {
            "signal_id": "signal_monitor_dashpro_supabase_storage_quota_warning",
            "severity": "high",
            "status": "open",
            "meta": {"signal_family": "child_project_monitor"},
        }
        summary = self.inbox_filters.summarize_actionable_inbox([high_item])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])

    def test_email_high_counts_as_high_not_critical(self) -> None:
        summary = self.inbox_filters.summarize_actionable_inbox([EMAIL_ITEM])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])
        self.assertEqual(EMAIL_ITEM, summary["top_items"][0])

    def test_bootstrap_excluded_when_email_signal_present(self) -> None:
        summary = self.inbox_filters.summarize_actionable_inbox([BOOTSTRAP_ITEM, EMAIL_ITEM])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])
        self.assertEqual(EMAIL_ITEM, summary["top_items"][0])

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records")
    def test_inbox_omits_bootstrap_when_monitor_signal_present(
        self, probe_monitors, _email_items, _acked
    ) -> None:
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
        payload = self.get_inbox_snapshot(connector_records=[])
        signal_ids = [
            str(item.get("signal_id"))
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        self.assertIn("signal_monitor_dashpro_sentry_recent_issues_critical", signal_ids)
        self.assertNotIn("signal_watch_bootstrap_ready", signal_ids)

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records")
    def test_inbox_omits_bootstrap_when_transport_warning_monitor_present(
        self, probe_monitors, _email_items, _acked
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
        payload = self.get_inbox_snapshot(connector_records=[])
        signal_ids = [
            str(item.get("signal_id"))
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        self.assertIn("signal_monitor_dashpro_posthog_recent_events_warning", signal_ids)
        self.assertNotIn("signal_watch_bootstrap_ready", signal_ids)

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records")
    def test_inbox_omits_bootstrap_when_sentry_transport_warning_present(
        self, probe_monitors, _email_items, _acked
    ) -> None:
        probe_monitors.return_value = [
            {
                "check_id": "dashpro_sentry_recent_issues",
                "check_type": "sentry_recent_issues",
                "service": "Sentry",
                "workspace_id": "workspace_dashpro",
                "workspace_label": "DashPro",
                "status": "warning",
                "detail": "Sentry API query failed: timed out",
            }
        ]
        payload = self.get_inbox_snapshot(connector_records=[])
        signal_ids = [
            str(item.get("signal_id"))
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        self.assertIn("signal_monitor_dashpro_sentry_recent_issues_warning", signal_ids)
        self.assertNotIn("signal_watch_bootstrap_ready", signal_ids)

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records")
    def test_inbox_omits_bootstrap_when_sentry_threshold_warning_present(
        self, probe_monitors, _email_items, _acked
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
        payload = self.get_inbox_snapshot(connector_records=[])
        signal_ids = [
            str(item.get("signal_id"))
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        self.assertIn("signal_monitor_dashpro_sentry_recent_issues_warning", signal_ids)
        self.assertNotIn("signal_watch_bootstrap_ready", signal_ids)
        monitor_items = [
            item
            for item in payload["items"]
            if str(item.get("signal_id", "")).startswith("signal_monitor_")
        ]
        self.assertEqual(1, len(monitor_items))
        self.assertEqual("high", monitor_items[0]["severity"])

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records")
    def test_inbox_omits_bootstrap_when_posthog_threshold_warning_present(
        self, probe_monitors, _email_items, _acked
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
        payload = self.get_inbox_snapshot(connector_records=[])
        signal_ids = [
            str(item.get("signal_id"))
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        self.assertIn("signal_monitor_dashpro_posthog_recent_events_warning", signal_ids)
        self.assertNotIn("signal_watch_bootstrap_ready", signal_ids)
        monitor_items = [
            item
            for item in payload["items"]
            if str(item.get("signal_id", "")).startswith("signal_monitor_")
        ]
        self.assertEqual(1, len(monitor_items))
        self.assertEqual("high", monitor_items[0]["severity"])

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records")
    def test_inbox_omits_bootstrap_when_posthog_critical_present(
        self, probe_monitors, _email_items, _acked
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
        payload = self.get_inbox_snapshot(connector_records=[])
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

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records")
    def test_inbox_omits_bootstrap_when_supabase_storage_critical_present(
        self, probe_monitors, _email_items, _acked
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
        payload = self.get_inbox_snapshot(connector_records=[])
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

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records")
    def test_inbox_omits_bootstrap_when_supabase_storage_threshold_warning_present(
        self, probe_monitors, _email_items, _acked
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
        payload = self.get_inbox_snapshot(connector_records=[])
        signal_ids = [
            str(item.get("signal_id"))
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        self.assertIn(
            "signal_monitor_dashpro_supabase_storage_quota_warning", signal_ids
        )
        self.assertNotIn("signal_watch_bootstrap_ready", signal_ids)
        monitor_items = [
            item
            for item in payload["items"]
            if str(item.get("signal_id", "")).startswith("signal_monitor_")
        ]
        self.assertEqual(1, len(monitor_items))
        self.assertEqual("high", monitor_items[0]["severity"])

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records", return_value=[])
    def test_inbox_omits_bootstrap_when_required_connector_fails(
        self, _monitors, _email_items, _acked
    ) -> None:
        payload = self.get_inbox_snapshot(
            connector_records=[
                {
                    "connector_id": "control_plane",
                    "display_name": "Control plane",
                    "status": "unavailable",
                    "required": True,
                },
            ]
        )
        signal_ids = [
            str(item.get("signal_id"))
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        self.assertIn("signal_connector_control_plane_unavailable", signal_ids)
        self.assertNotIn("signal_watch_bootstrap_ready", signal_ids)

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records", return_value=[])
    def test_inbox_omits_bootstrap_when_required_connector_degraded(
        self, _monitors, _email_items, _acked
    ) -> None:
        payload = self.get_inbox_snapshot(
            connector_records=[
                {
                    "connector_id": "console_web",
                    "display_name": "Console web",
                    "status": "degraded",
                    "required": True,
                    "detail": "status=503",
                },
            ]
        )
        signal_ids = [
            str(item.get("signal_id"))
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        self.assertIn("signal_connector_console_web_degraded", signal_ids)
        self.assertNotIn("signal_watch_bootstrap_ready", signal_ids)

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records", return_value=[])
    def test_inbox_omits_bootstrap_when_optional_tunnel_stale_ingress_degraded(
        self, _monitors, _email_items, _acked
    ) -> None:
        payload = self.get_inbox_snapshot(
            connector_records=[
                {
                    "connector_id": "control_plane",
                    "display_name": "Control plane",
                    "status": "ok",
                    "required": True,
                },
                {
                    "connector_id": "cloudflare_tunnel",
                    "display_name": "Cloudflare tunnel",
                    "status": "degraded",
                    "required": False,
                    "detail": "ingress still targets stale local origin",
                    "tunnel": {"ingress_matches_axon": False},
                },
            ]
        )
        signal_ids = [
            str(item.get("signal_id"))
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        self.assertIn("signal_connector_cloudflare_tunnel_degraded", signal_ids)
        self.assertNotIn("signal_watch_bootstrap_ready", signal_ids)
        connector_items = [
            item
            for item in payload["items"]
            if str(item.get("source")) == "connector"
        ]
        self.assertEqual(1, len(connector_items))
        self.assertEqual("high", connector_items[0]["severity"])
        self.assertEqual("investigate", connector_items[0]["action_type"])

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.probe_monitor_records", return_value=[])
    def test_inbox_omits_bootstrap_when_email_signal_present(
        self, _monitors, _acked
    ) -> None:
        with patch(
            "app.signals.store.email_inbox_items",
            return_value=[EMAIL_ITEM],
        ):
            payload = self.get_inbox_snapshot(connector_records=[])
        signal_ids = [
            str(item.get("signal_id"))
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        self.assertIn("signal_email_stub_invoice", signal_ids)
        self.assertNotIn("signal_watch_bootstrap_ready", signal_ids)


if __name__ == "__main__":
    unittest.main()
