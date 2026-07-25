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
)
from tests.support.control_plane_app_loader import load_control_plane_app, prepare_control_plane_imports
from tests.support.email_signal_fixture import EMAIL_INBOX_ITEM, EMAIL_WATCH_INBOX
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
from tests.support.summary_degraded_signal_fixture import SUMMARY_DEGRADED_INBOX_ITEM


class SignalConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        prepare_control_plane_imports()
        from app.inbox_projection import project_watch_inbox  # noqa: WPS433
        from app.runtime_summary_assembler import assemble_runtime_summary  # noqa: WPS433

        self.project_watch_inbox = project_watch_inbox
        self.assemble_runtime_summary = assemble_runtime_summary
        self.client = TestClient(load_control_plane_app())
        self.addCleanup(self.client.close)

    def test_control_plane_projection_preserves_watch_bootstrap_consistency_fields(self) -> None:
        projected_item = self.project_watch_inbox(BOOTSTRAP_WATCH_INBOX)["items"][0]
        self.assertEqual(
            consistency_tuple(BOOTSTRAP_INBOX_ITEM),
            consistency_tuple(projected_item),
        )

    def test_runtime_summary_top_item_matches_watch_bootstrap_item(self) -> None:
        summary = self.assemble_runtime_summary(
            watch_probe=lambda: (True, "ok", None, "2026-07-03T16:00:00Z"),
            inbox_fetcher=lambda: BOOTSTRAP_WATCH_INBOX,
        )
        self.assertEqual(0, summary["signals"]["open_count"])
        self.assertEqual([], summary["signals"]["top_items"])

    def test_control_plane_inbox_and_runtime_summary_endpoints_agree(self) -> None:
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=BOOTSTRAP_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.fetch_watch_inbox",
            return_value=BOOTSTRAP_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-03T16:00:00Z"),
        ):
            inbox_item = self.client.get("/api/inbox").json()["items"][0]
            summary = self.client.get("/api/runtime/summary").json()["signals"]

        self.assertEqual(consistency_tuple(BOOTSTRAP_INBOX_ITEM), consistency_tuple(inbox_item))
        self.assertEqual(0, summary["open_count"])
        self.assertEqual([], summary["top_items"])

    def test_control_plane_inbox_and_runtime_summary_preserve_ranked_top_signal(self) -> None:
        ranked_watch_inbox = {
            "items": [SUMMARY_DEGRADED_INBOX_ITEM, BOOTSTRAP_INBOX_ITEM],
            "count": 2,
            "updated_at": "2026-07-03T16:00:00Z",
        }
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=ranked_watch_inbox,
        ), patch(
            "app.runtime_summary_assembler.fetch_watch_inbox",
            return_value=ranked_watch_inbox,
        ), patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-03T16:00:00Z"),
        ):
            inbox_item = self.client.get("/api/inbox").json()["items"][0]
            summary = self.client.get("/api/runtime/summary").json()["signals"]

        self.assertEqual(
            consistency_tuple(SUMMARY_DEGRADED_INBOX_ITEM),
            consistency_tuple(inbox_item),
        )
        self.assertEqual(0, summary["open_count"])
        self.assertEqual([], summary["top_items"])

    def test_control_plane_preserves_email_signal_across_inbox_and_summary(self) -> None:
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=EMAIL_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.fetch_watch_inbox",
            return_value=EMAIL_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-13T12:00:00Z"),
        ):
            inbox_item = self.client.get("/api/inbox").json()["items"][0]
            summary = self.client.get("/api/runtime/summary").json()["signals"]

        self.assertEqual(consistency_tuple(EMAIL_INBOX_ITEM), consistency_tuple(inbox_item))
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])
        self.assertEqual(
            consistency_tuple(EMAIL_INBOX_ITEM),
            consistency_tuple(summary["top_items"][0]),
        )
        self.assertEqual("email", inbox_item["source"])
        self.assertEqual("high", inbox_item["severity"])

    def test_control_plane_preserves_connector_signal_across_inbox_and_summary(self) -> None:
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=CONNECTOR_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.fetch_watch_inbox",
            return_value=CONNECTOR_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-17T06:00:00Z"),
        ):
            inbox_item = self.client.get("/api/inbox").json()["items"][0]
            summary = self.client.get("/api/runtime/summary").json()["signals"]

        self.assertEqual(
            consistency_tuple(CONNECTOR_INBOX_ITEM),
            consistency_tuple(inbox_item),
        )
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(
            consistency_tuple(CONNECTOR_INBOX_ITEM),
            consistency_tuple(summary["top_items"][0]),
        )
        self.assertEqual("connector", inbox_item["source"])

    def test_control_plane_preserves_connector_degraded_signal_across_inbox_and_summary(
        self,
    ) -> None:
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=CONNECTOR_DEGRADED_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.fetch_watch_inbox",
            return_value=CONNECTOR_DEGRADED_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-17T06:00:00Z"),
        ):
            inbox_item = self.client.get("/api/inbox").json()["items"][0]
            summary = self.client.get("/api/runtime/summary").json()["signals"]

        self.assertEqual(
            consistency_tuple(CONNECTOR_DEGRADED_INBOX_ITEM),
            consistency_tuple(inbox_item),
        )
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])
        self.assertEqual(
            consistency_tuple(CONNECTOR_DEGRADED_INBOX_ITEM),
            consistency_tuple(summary["top_items"][0]),
        )
        self.assertEqual("high", inbox_item["severity"])

    def test_control_plane_preserves_connector_over_summary_degraded(self) -> None:
        ranked_watch_inbox = {
            "items": [CONNECTOR_INBOX_ITEM, SUMMARY_DEGRADED_INBOX_ITEM],
            "count": 2,
            "updated_at": "2026-07-17T06:00:00Z",
        }
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=ranked_watch_inbox,
        ), patch(
            "app.runtime_summary_assembler.fetch_watch_inbox",
            return_value=ranked_watch_inbox,
        ), patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-17T06:00:00Z"),
        ):
            inbox_item = self.client.get("/api/inbox").json()["items"][0]
            summary = self.client.get("/api/runtime/summary").json()["signals"]

        self.assertEqual(
            consistency_tuple(CONNECTOR_INBOX_ITEM),
            consistency_tuple(inbox_item),
        )
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(1, summary["critical_count"])
        self.assertEqual(
            consistency_tuple(CONNECTOR_INBOX_ITEM),
            consistency_tuple(summary["top_items"][0]),
        )

    def test_control_plane_preserves_connector_degraded_over_summary_degraded(
        self,
    ) -> None:
        ranked_watch_inbox = {
            "items": [CONNECTOR_DEGRADED_INBOX_ITEM, SUMMARY_DEGRADED_INBOX_ITEM],
            "count": 2,
            "updated_at": "2026-07-17T06:00:00Z",
        }
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=ranked_watch_inbox,
        ), patch(
            "app.runtime_summary_assembler.fetch_watch_inbox",
            return_value=ranked_watch_inbox,
        ), patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-17T06:00:00Z"),
        ):
            inbox_item = self.client.get("/api/inbox").json()["items"][0]
            summary = self.client.get("/api/runtime/summary").json()["signals"]

        self.assertEqual(
            consistency_tuple(CONNECTOR_DEGRADED_INBOX_ITEM),
            consistency_tuple(inbox_item),
        )
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])
        self.assertEqual(
            consistency_tuple(CONNECTOR_DEGRADED_INBOX_ITEM),
            consistency_tuple(summary["top_items"][0]),
        )

    def test_control_plane_preserves_sentry_monitor_signal_across_inbox_and_summary(self) -> None:
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=SENTRY_MONITOR_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.fetch_watch_inbox",
            return_value=SENTRY_MONITOR_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-17T06:00:00Z"),
        ):
            inbox_item = self.client.get("/api/inbox").json()["items"][0]
            summary = self.client.get("/api/runtime/summary").json()["signals"]

        self.assertEqual(
            consistency_tuple(SENTRY_MONITOR_INBOX_ITEM),
            consistency_tuple(inbox_item),
        )
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(
            consistency_tuple(SENTRY_MONITOR_INBOX_ITEM),
            consistency_tuple(summary["top_items"][0]),
        )
        self.assertEqual("watch", inbox_item["source"])

        for surface in (inbox_item, summary["top_items"][0]):
            meta = surface.get("meta")
            self.assertIsInstance(meta, dict)
            assert isinstance(meta, dict)
            self.assertEqual(SENTRY_ISSUES, meta.get("sentry_issues"))
            self.assertEqual(len(SENTRY_ISSUES), meta.get("sentry_issue_count"))

    def test_control_plane_preserves_posthog_transport_warning_across_inbox_and_summary(
        self,
    ) -> None:
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=POSTHOG_TRANSPORT_WARNING_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.fetch_watch_inbox",
            return_value=POSTHOG_TRANSPORT_WARNING_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-17T06:00:00Z"),
        ):
            inbox_item = self.client.get("/api/inbox").json()["items"][0]
            summary = self.client.get("/api/runtime/summary").json()["signals"]

        self.assertEqual(
            consistency_tuple(POSTHOG_TRANSPORT_WARNING_INBOX_ITEM),
            consistency_tuple(inbox_item),
        )
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(0, summary["high_count"])
        self.assertEqual(
            consistency_tuple(POSTHOG_TRANSPORT_WARNING_INBOX_ITEM),
            consistency_tuple(summary["top_items"][0]),
        )
        self.assertEqual("warning", inbox_item["severity"])

    def test_control_plane_preserves_sentry_transport_warning_across_inbox_and_summary(
        self,
    ) -> None:
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=SENTRY_TRANSPORT_WARNING_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.fetch_watch_inbox",
            return_value=SENTRY_TRANSPORT_WARNING_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-17T06:00:00Z"),
        ):
            inbox_item = self.client.get("/api/inbox").json()["items"][0]
            summary = self.client.get("/api/runtime/summary").json()["signals"]

        self.assertEqual(
            consistency_tuple(SENTRY_TRANSPORT_WARNING_INBOX_ITEM),
            consistency_tuple(inbox_item),
        )
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(0, summary["high_count"])
        self.assertEqual(
            consistency_tuple(SENTRY_TRANSPORT_WARNING_INBOX_ITEM),
            consistency_tuple(summary["top_items"][0]),
        )
        self.assertEqual("warning", inbox_item["severity"])

    def test_control_plane_preserves_sentry_threshold_warning_across_inbox_and_summary(
        self,
    ) -> None:
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=SENTRY_THRESHOLD_WARNING_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.fetch_watch_inbox",
            return_value=SENTRY_THRESHOLD_WARNING_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-17T06:00:00Z"),
        ):
            inbox_item = self.client.get("/api/inbox").json()["items"][0]
            summary = self.client.get("/api/runtime/summary").json()["signals"]

        self.assertEqual(
            consistency_tuple(SENTRY_THRESHOLD_WARNING_INBOX_ITEM),
            consistency_tuple(inbox_item),
        )
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])
        self.assertEqual(
            consistency_tuple(SENTRY_THRESHOLD_WARNING_INBOX_ITEM),
            consistency_tuple(summary["top_items"][0]),
        )
        self.assertEqual("high", inbox_item["severity"])

        for surface in (inbox_item, summary["top_items"][0]):
            meta = surface.get("meta")
            self.assertIsInstance(meta, dict)
            assert isinstance(meta, dict)
            self.assertEqual(SENTRY_THRESHOLD_ISSUES, meta.get("sentry_issues"))
            self.assertEqual(len(SENTRY_THRESHOLD_ISSUES), meta.get("sentry_issue_count"))

    def test_control_plane_preserves_posthog_threshold_warning_across_inbox_and_summary(
        self,
    ) -> None:
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=POSTHOG_THRESHOLD_WARNING_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.fetch_watch_inbox",
            return_value=POSTHOG_THRESHOLD_WARNING_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-17T06:00:00Z"),
        ):
            inbox_item = self.client.get("/api/inbox").json()["items"][0]
            summary = self.client.get("/api/runtime/summary").json()["signals"]

        self.assertEqual(
            consistency_tuple(POSTHOG_THRESHOLD_WARNING_INBOX_ITEM),
            consistency_tuple(inbox_item),
        )
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])
        self.assertEqual(
            consistency_tuple(POSTHOG_THRESHOLD_WARNING_INBOX_ITEM),
            consistency_tuple(summary["top_items"][0]),
        )
        self.assertEqual("high", inbox_item["severity"])

    def test_control_plane_preserves_posthog_critical_across_inbox_and_summary(self) -> None:
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=POSTHOG_CRITICAL_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.fetch_watch_inbox",
            return_value=POSTHOG_CRITICAL_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-17T06:00:00Z"),
        ):
            inbox_item = self.client.get("/api/inbox").json()["items"][0]
            summary = self.client.get("/api/runtime/summary").json()["signals"]

        self.assertEqual(
            consistency_tuple(POSTHOG_CRITICAL_INBOX_ITEM),
            consistency_tuple(inbox_item),
        )
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(1, summary["critical_count"])
        self.assertEqual(0, summary["high_count"])
        self.assertEqual(
            consistency_tuple(POSTHOG_CRITICAL_INBOX_ITEM),
            consistency_tuple(summary["top_items"][0]),
        )
        self.assertEqual("critical", inbox_item["severity"])
        self.assertEqual("watch", inbox_item["source"])

    def test_control_plane_preserves_supabase_storage_critical_across_inbox_and_summary(
        self,
    ) -> None:
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=SUPABASE_STORAGE_CRITICAL_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.fetch_watch_inbox",
            return_value=SUPABASE_STORAGE_CRITICAL_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-17T06:00:00Z"),
        ):
            inbox_item = self.client.get("/api/inbox").json()["items"][0]
            summary = self.client.get("/api/runtime/summary").json()["signals"]

        self.assertEqual(
            consistency_tuple(SUPABASE_STORAGE_CRITICAL_INBOX_ITEM),
            consistency_tuple(inbox_item),
        )
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(1, summary["critical_count"])
        self.assertEqual(0, summary["high_count"])
        self.assertEqual(
            consistency_tuple(SUPABASE_STORAGE_CRITICAL_INBOX_ITEM),
            consistency_tuple(summary["top_items"][0]),
        )
        self.assertEqual("critical", inbox_item["severity"])
        self.assertEqual("watch", inbox_item["source"])

        for surface in (inbox_item, summary["top_items"][0]):
            meta = surface.get("meta")
            self.assertIsInstance(meta, dict)
            assert isinstance(meta, dict)
            self.assertEqual("dashpro_supabase_storage_quota", meta.get("check_id"))
            self.assertEqual("supabase_storage_quota", meta.get("check_type"))

    def test_control_plane_preserves_supabase_storage_threshold_warning_across_inbox_and_summary(
        self,
    ) -> None:
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=SUPABASE_STORAGE_THRESHOLD_WARNING_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.fetch_watch_inbox",
            return_value=SUPABASE_STORAGE_THRESHOLD_WARNING_WATCH_INBOX,
        ), patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-17T06:00:00Z"),
        ):
            inbox_item = self.client.get("/api/inbox").json()["items"][0]
            summary = self.client.get("/api/runtime/summary").json()["signals"]

        self.assertEqual(
            consistency_tuple(SUPABASE_STORAGE_THRESHOLD_WARNING_INBOX_ITEM),
            consistency_tuple(inbox_item),
        )
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(0, summary["critical_count"])
        self.assertEqual(1, summary["high_count"])
        self.assertEqual(
            consistency_tuple(SUPABASE_STORAGE_THRESHOLD_WARNING_INBOX_ITEM),
            consistency_tuple(summary["top_items"][0]),
        )
        self.assertEqual("high", inbox_item["severity"])


if __name__ == "__main__":
    unittest.main()
