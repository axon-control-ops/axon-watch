"""P-A4 signal/inbox consistency cross-surface parity tests."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.bootstrap_signal_fixture import (
    BOOTSTRAP_INBOX_ITEM,
    BOOTSTRAP_WATCH_INBOX,
    consistency_tuple,
)
from tests.support.connector_signal_fixture import (
    CONNECTOR_DEGRADED_INBOX_ITEM,
    CONNECTOR_DEGRADED_WATCH_INBOX,
    CONNECTOR_INBOX_ITEM,
    CONNECTOR_WATCH_INBOX,
    OPTIONAL_TUNNEL_LEGACY_INGRESS_INBOX_ITEM,
    OPTIONAL_TUNNEL_LEGACY_INGRESS_WATCH_INBOX,
)
from tests.support.email_signal_fixture import EMAIL_INBOX_ITEM, EMAIL_WATCH_INBOX
from tests.support.control_plane_app_loader import load_control_plane_app, prepare_control_plane_imports
from tests.support.summary_degraded_signal_fixture import SUMMARY_DEGRADED_INBOX_ITEM
from tests.support.monitor_signal_fixture import (
    POSTHOG_CRITICAL_INBOX_ITEM,
    POSTHOG_CRITICAL_WATCH_INBOX,
    POSTHOG_THRESHOLD_WARNING_INBOX_ITEM,
    POSTHOG_THRESHOLD_WARNING_WATCH_INBOX,
    POSTHOG_TRANSPORT_WARNING_INBOX_ITEM,
    POSTHOG_TRANSPORT_WARNING_WATCH_INBOX,
    SENTRY_ISSUES,
    SENTRY_MONITOR_INBOX_ITEM,
    SENTRY_MONITOR_WATCH_INBOX,
    SENTRY_THRESHOLD_ISSUES,
    SENTRY_THRESHOLD_WARNING_INBOX_ITEM,
    SENTRY_THRESHOLD_WARNING_WATCH_INBOX,
    SENTRY_TRANSPORT_WARNING_INBOX_ITEM,
    SENTRY_TRANSPORT_WARNING_WATCH_INBOX,
    SUPABASE_STORAGE_CRITICAL_INBOX_ITEM,
    SUPABASE_STORAGE_CRITICAL_WATCH_INBOX,
    SUPABASE_STORAGE_THRESHOLD_WARNING_INBOX_ITEM,
    SUPABASE_STORAGE_THRESHOLD_WARNING_WATCH_INBOX,
)

ACTIONABLE_MONITOR_ITEM = {
    "signal_id": "signal_monitor_dashpro_storage",
    "workspace_id": "workspace_dashpro",
    "title": "DashPro storage probe failed",
    "summary": "Child-project monitor reported a storage failure.",
    "severity": "high",
    "status": "open",
    "source": "watch",
    "created_at": "2026-07-05T10:00:00Z",
    "updated_at": "2026-07-05T10:00:00Z",
    "action_type": "open_dashboard",
    "meta": {"signal_family": "child_project_monitor"},
}


class ParityA4SignalInboxConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        prepare_control_plane_imports()
        self.client = TestClient(load_control_plane_app())
        self.addCleanup(self.client.close)

    def _patch_watch_inbox(self, inbox: dict[str, object]) -> None:
        self._inbox_patch = patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=inbox,
        )
        self._summary_patch = patch(
            "app.runtime_summary_assembler.fetch_watch_inbox",
            return_value=inbox,
        )
        self._probe_patch = patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-05T10:00:00Z"),
        )
        self._inbox_patch.start()
        self._summary_patch.start()
        self._probe_patch.start()

    def tearDown(self) -> None:
        for patcher in (
            getattr(self, "_probe_patch", None),
            getattr(self, "_summary_patch", None),
            getattr(self, "_inbox_patch", None),
        ):
            if patcher is not None:
                patcher.stop()

    def test_bootstrap_signal_consistent_across_inbox_summary_and_briefing(self) -> None:
        self._patch_watch_inbox(BOOTSTRAP_WATCH_INBOX)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(BOOTSTRAP_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        # Runtime summary filters bootstrap-only noise from signal counts.
        self.assertEqual(0, summary["open_count"])
        self.assertEqual([], summary["top_items"])

    def test_ranked_top_signal_consistent_across_all_surfaces(self) -> None:
        ranked_inbox = {
            "items": [ACTIONABLE_MONITOR_ITEM, BOOTSTRAP_INBOX_ITEM],
            "count": 2,
            "updated_at": "2026-07-05T10:00:00Z",
        }
        self._patch_watch_inbox(ranked_inbox)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary_item = self.client.get("/api/runtime/summary").json()["signals"]["top_items"][0]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(ACTIONABLE_MONITOR_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary_item))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual("high", inbox_item["severity"])

    def test_email_signal_consistent_across_inbox_summary_and_briefing(self) -> None:
        self._patch_watch_inbox(EMAIL_WATCH_INBOX)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary_item = self.client.get("/api/runtime/summary").json()["signals"]["top_items"][0]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(EMAIL_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary_item))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual("email", inbox_item["source"])
        self.assertEqual("workspace_dashpro", inbox_item["workspace_id"])
        self.assertEqual("email_triage", inbox_item.get("meta", {}).get("signal_family"))
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        self.assertEqual("high", inbox_item["severity"])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])

    def test_email_signal_wins_over_bootstrap_in_summary_and_briefing(self) -> None:
        ranked_inbox = {
            "items": [EMAIL_INBOX_ITEM, BOOTSTRAP_INBOX_ITEM],
            "count": 2,
            "updated_at": "2026-07-13T12:00:00Z",
        }
        self._patch_watch_inbox(ranked_inbox)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(EMAIL_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])

    def test_connector_signal_consistent_across_inbox_summary_and_briefing(self) -> None:
        self._patch_watch_inbox(CONNECTOR_WATCH_INBOX)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary_item = self.client.get("/api/runtime/summary").json()["signals"]["top_items"][0]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(CONNECTOR_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary_item))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual("connector", inbox_item["source"])
        self.assertEqual("workspace_axon_watch", inbox_item["workspace_id"])
        self.assertEqual(1, self.client.get("/api/runtime/summary").json()["signals"]["open_count"])
        self.assertEqual(1, self.client.get("/api/runtime/summary").json()["signals"]["critical_count"])

    def test_connector_signal_wins_over_bootstrap_in_summary_and_briefing(self) -> None:
        ranked_inbox = {
            "items": [CONNECTOR_INBOX_ITEM, BOOTSTRAP_INBOX_ITEM],
            "count": 2,
            "updated_at": "2026-07-17T06:00:00Z",
        }
        self._patch_watch_inbox(ranked_inbox)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(CONNECTOR_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(1, summary["critical_count"])

    def test_connector_degraded_signal_consistent_across_inbox_summary_and_briefing(
        self,
    ) -> None:
        self._patch_watch_inbox(CONNECTOR_DEGRADED_WATCH_INBOX)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(CONNECTOR_DEGRADED_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual("high", inbox_item["severity"])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])

    def test_connector_degraded_signal_wins_over_bootstrap_in_summary_and_briefing(
        self,
    ) -> None:
        ranked_inbox = {
            "items": [CONNECTOR_DEGRADED_INBOX_ITEM, BOOTSTRAP_INBOX_ITEM],
            "count": 2,
            "updated_at": "2026-07-17T06:00:00Z",
        }
        self._patch_watch_inbox(ranked_inbox)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(CONNECTOR_DEGRADED_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])

    def test_optional_tunnel_legacy_ingress_signal_consistent_across_surfaces(
        self,
    ) -> None:
        self._patch_watch_inbox(OPTIONAL_TUNNEL_LEGACY_INGRESS_WATCH_INBOX)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(OPTIONAL_TUNNEL_LEGACY_INGRESS_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual("high", inbox_item["severity"])
        self.assertEqual("investigate", inbox_item["action_type"])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])

    def test_connector_signal_wins_over_summary_degraded_in_summary_and_briefing(
        self,
    ) -> None:
        ranked_inbox = {
            "items": [CONNECTOR_INBOX_ITEM, SUMMARY_DEGRADED_INBOX_ITEM],
            "count": 2,
            "updated_at": "2026-07-17T06:00:00Z",
        }
        self._patch_watch_inbox(ranked_inbox)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(CONNECTOR_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(1, summary["critical_count"])
        self.assertEqual(0, summary["high_count"])

    def test_connector_degraded_signal_wins_over_summary_degraded_in_summary_and_briefing(
        self,
    ) -> None:
        ranked_inbox = {
            "items": [CONNECTOR_DEGRADED_INBOX_ITEM, SUMMARY_DEGRADED_INBOX_ITEM],
            "count": 2,
            "updated_at": "2026-07-17T06:00:00Z",
        }
        self._patch_watch_inbox(ranked_inbox)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(CONNECTOR_DEGRADED_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])

    def test_sentry_monitor_signal_consistent_across_inbox_summary_and_briefing(self) -> None:
        self._patch_watch_inbox(SENTRY_MONITOR_WATCH_INBOX)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary_item = self.client.get("/api/runtime/summary").json()["signals"]["top_items"][0]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(SENTRY_MONITOR_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary_item))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual("watch", inbox_item["source"])
        self.assertEqual("workspace_dashpro", inbox_item["workspace_id"])
        self.assertEqual(1, self.client.get("/api/runtime/summary").json()["signals"]["open_count"])
        self.assertEqual(1, self.client.get("/api/runtime/summary").json()["signals"]["critical_count"])

        for surface in (inbox_item, summary_item, briefing_item):
            meta = surface.get("meta")
            self.assertIsInstance(meta, dict)
            assert isinstance(meta, dict)
            self.assertEqual(SENTRY_ISSUES, meta.get("sentry_issues"))
            self.assertEqual(len(SENTRY_ISSUES), meta.get("sentry_issue_count"))

    def test_sentry_monitor_signal_wins_over_bootstrap_in_summary_and_briefing(self) -> None:
        ranked_inbox = {
            "items": [SENTRY_MONITOR_INBOX_ITEM, BOOTSTRAP_INBOX_ITEM],
            "count": 2,
            "updated_at": "2026-07-17T06:00:00Z",
        }
        self._patch_watch_inbox(ranked_inbox)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(SENTRY_MONITOR_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(1, summary["critical_count"])

    def test_posthog_transport_warning_consistent_across_inbox_summary_and_briefing(
        self,
    ) -> None:
        self._patch_watch_inbox(POSTHOG_TRANSPORT_WARNING_WATCH_INBOX)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(POSTHOG_TRANSPORT_WARNING_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual("warning", inbox_item["severity"])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(0, summary["high_count"])

    def test_posthog_transport_warning_wins_over_bootstrap_in_summary_and_briefing(
        self,
    ) -> None:
        ranked_inbox = {
            "items": [POSTHOG_TRANSPORT_WARNING_INBOX_ITEM, BOOTSTRAP_INBOX_ITEM],
            "count": 2,
            "updated_at": "2026-07-17T06:00:00Z",
        }
        self._patch_watch_inbox(ranked_inbox)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(POSTHOG_TRANSPORT_WARNING_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])

    def test_sentry_transport_warning_consistent_across_inbox_summary_and_briefing(
        self,
    ) -> None:
        self._patch_watch_inbox(SENTRY_TRANSPORT_WARNING_WATCH_INBOX)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(SENTRY_TRANSPORT_WARNING_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual("warning", inbox_item["severity"])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(0, summary["high_count"])

    def test_sentry_transport_warning_wins_over_bootstrap_in_summary_and_briefing(
        self,
    ) -> None:
        ranked_inbox = {
            "items": [SENTRY_TRANSPORT_WARNING_INBOX_ITEM, BOOTSTRAP_INBOX_ITEM],
            "count": 2,
            "updated_at": "2026-07-17T06:00:00Z",
        }
        self._patch_watch_inbox(ranked_inbox)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(SENTRY_TRANSPORT_WARNING_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])

    def test_sentry_threshold_warning_consistent_across_inbox_summary_and_briefing(
        self,
    ) -> None:
        self._patch_watch_inbox(SENTRY_THRESHOLD_WARNING_WATCH_INBOX)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(SENTRY_THRESHOLD_WARNING_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual("high", inbox_item["severity"])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])

        for surface in (inbox_item, summary["top_items"][0], briefing_item):
            meta = surface.get("meta")
            self.assertIsInstance(meta, dict)
            assert isinstance(meta, dict)
            self.assertEqual(SENTRY_THRESHOLD_ISSUES, meta.get("sentry_issues"))
            self.assertEqual(len(SENTRY_THRESHOLD_ISSUES), meta.get("sentry_issue_count"))

    def test_sentry_threshold_warning_wins_over_bootstrap_in_summary_and_briefing(
        self,
    ) -> None:
        ranked_inbox = {
            "items": [SENTRY_THRESHOLD_WARNING_INBOX_ITEM, BOOTSTRAP_INBOX_ITEM],
            "count": 2,
            "updated_at": "2026-07-17T06:00:00Z",
        }
        self._patch_watch_inbox(ranked_inbox)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(SENTRY_THRESHOLD_WARNING_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])

    def test_posthog_threshold_warning_consistent_across_inbox_summary_and_briefing(
        self,
    ) -> None:
        self._patch_watch_inbox(POSTHOG_THRESHOLD_WARNING_WATCH_INBOX)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(POSTHOG_THRESHOLD_WARNING_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual("high", inbox_item["severity"])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])

    def test_posthog_threshold_warning_wins_over_bootstrap_in_summary_and_briefing(
        self,
    ) -> None:
        ranked_inbox = {
            "items": [POSTHOG_THRESHOLD_WARNING_INBOX_ITEM, BOOTSTRAP_INBOX_ITEM],
            "count": 2,
            "updated_at": "2026-07-17T06:00:00Z",
        }
        self._patch_watch_inbox(ranked_inbox)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(POSTHOG_THRESHOLD_WARNING_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])

    def test_posthog_critical_consistent_across_inbox_summary_and_briefing(self) -> None:
        self._patch_watch_inbox(POSTHOG_CRITICAL_WATCH_INBOX)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(POSTHOG_CRITICAL_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual("critical", inbox_item["severity"])
        self.assertEqual("watch", inbox_item["source"])
        self.assertEqual("workspace_dashpro", inbox_item["workspace_id"])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(1, summary["critical_count"])
        self.assertEqual(0, summary["high_count"])

    def test_posthog_critical_wins_over_bootstrap_in_summary_and_briefing(self) -> None:
        ranked_inbox = {
            "items": [POSTHOG_CRITICAL_INBOX_ITEM, BOOTSTRAP_INBOX_ITEM],
            "count": 2,
            "updated_at": "2026-07-17T06:00:00Z",
        }
        self._patch_watch_inbox(ranked_inbox)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(POSTHOG_CRITICAL_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(1, summary["critical_count"])
        self.assertEqual(0, summary["high_count"])

    def test_supabase_storage_critical_consistent_across_inbox_summary_and_briefing(
        self,
    ) -> None:
        self._patch_watch_inbox(SUPABASE_STORAGE_CRITICAL_WATCH_INBOX)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(SUPABASE_STORAGE_CRITICAL_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual("critical", inbox_item["severity"])
        self.assertEqual("watch", inbox_item["source"])
        self.assertEqual("workspace_dashpro", inbox_item["workspace_id"])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(1, summary["critical_count"])
        self.assertEqual(0, summary["high_count"])

        for surface in (inbox_item, summary["top_items"][0], briefing_item):
            meta = surface.get("meta")
            self.assertIsInstance(meta, dict)
            assert isinstance(meta, dict)
            self.assertEqual("dashpro_supabase_storage_quota", meta.get("check_id"))
            self.assertEqual("supabase_storage_quota", meta.get("check_type"))
            self.assertEqual("critical", meta.get("monitor_status"))

    def test_supabase_storage_critical_wins_over_bootstrap_in_summary_and_briefing(
        self,
    ) -> None:
        ranked_inbox = {
            "items": [SUPABASE_STORAGE_CRITICAL_INBOX_ITEM, BOOTSTRAP_INBOX_ITEM],
            "count": 2,
            "updated_at": "2026-07-17T06:00:00Z",
        }
        self._patch_watch_inbox(ranked_inbox)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(SUPABASE_STORAGE_CRITICAL_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(1, summary["critical_count"])
        self.assertEqual(0, summary["high_count"])

    def test_supabase_storage_threshold_warning_consistent_across_inbox_summary_and_briefing(
        self,
    ) -> None:
        self._patch_watch_inbox(SUPABASE_STORAGE_THRESHOLD_WARNING_WATCH_INBOX)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(SUPABASE_STORAGE_THRESHOLD_WARNING_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual("high", inbox_item["severity"])
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])

    def test_supabase_storage_threshold_warning_wins_over_bootstrap_in_summary_and_briefing(
        self,
    ) -> None:
        ranked_inbox = {
            "items": [
                SUPABASE_STORAGE_THRESHOLD_WARNING_INBOX_ITEM,
                BOOTSTRAP_INBOX_ITEM,
            ],
            "count": 2,
            "updated_at": "2026-07-17T06:00:00Z",
        }
        self._patch_watch_inbox(ranked_inbox)

        inbox_item = self.client.get("/api/inbox").json()["items"][0]
        summary = self.client.get("/api/runtime/summary").json()["signals"]
        briefing_item = self.client.get("/api/briefing").json()["top_signals"][0]

        expected = consistency_tuple(SUPABASE_STORAGE_THRESHOLD_WARNING_INBOX_ITEM)
        self.assertEqual(expected, consistency_tuple(inbox_item))
        self.assertEqual(expected, consistency_tuple(summary["top_items"][0]))
        self.assertEqual(expected, consistency_tuple(briefing_item))
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])


if __name__ == "__main__":
    unittest.main()
