"""P-A4 signal/inbox consistency cross-surface parity tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.bootstrap_signal_fixture import (
    BOOTSTRAP_INBOX_ITEM,
    BOOTSTRAP_WATCH_INBOX,
    consistency_tuple,
)

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402

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
        self.client = TestClient(app)

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


if __name__ == "__main__":
    unittest.main()
