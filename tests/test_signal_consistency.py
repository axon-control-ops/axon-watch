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

from app.inbox_projection import project_watch_inbox  # noqa: E402
from app.main import app  # noqa: E402
from app.runtime_summary_assembler import assemble_runtime_summary  # noqa: E402


class SignalConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_control_plane_projection_preserves_watch_bootstrap_consistency_fields(self) -> None:
        projected_item = project_watch_inbox(BOOTSTRAP_WATCH_INBOX)["items"][0]
        self.assertEqual(
            consistency_tuple(BOOTSTRAP_INBOX_ITEM),
            consistency_tuple(projected_item),
        )

    def test_runtime_summary_top_item_matches_watch_bootstrap_item(self) -> None:
        summary = assemble_runtime_summary(
            watch_probe=lambda: (True, "ok", None, "2026-07-03T16:00:00Z"),
            inbox_fetcher=lambda: BOOTSTRAP_WATCH_INBOX,
        )
        top_item = summary["signals"]["top_items"][0]

        self.assertEqual(consistency_tuple(BOOTSTRAP_INBOX_ITEM), consistency_tuple(top_item))
        self.assertEqual(1, summary["signals"]["open_count"])

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
            summary_item = self.client.get("/api/runtime/summary").json()["signals"]["top_items"][0]

        self.assertEqual(consistency_tuple(BOOTSTRAP_INBOX_ITEM), consistency_tuple(inbox_item))
        self.assertEqual(consistency_tuple(inbox_item), consistency_tuple(summary_item))


if __name__ == "__main__":
    unittest.main()
