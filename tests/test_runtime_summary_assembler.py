from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.runs.service import create_run  # noqa: E402
from app.runtime_summary_assembler import assemble_runtime_summary  # noqa: E402

from scripts.verify.common import load_config  # noqa: E402

_CANONICAL_TOP_LEVEL_KEYS = {
    "generated_at",
    "control_plane",
    "watch",
    "runtime_identity",
    "active_runs",
    "approvals",
    "signals",
    "connectors",
    "cli_runtime",
    "capabilities",
    "degraded",
}


def _connected_probe() -> tuple[bool, str, str | None, str]:
    return True, "ok", None, "2026-07-03T15:00:00Z"


def _disconnected_probe() -> tuple[bool, str, str | None, str]:
    return False, "unavailable", "watch probe failed", "2026-07-03T15:00:00Z"


class RuntimeSummaryAssemblerTests(unittest.TestCase):
    def setUp(self) -> None:
        from app.persistence import run_store

        isolate_control_plane_db(self, run_store)

    def test_assembler_returns_canonical_top_level_shape(self) -> None:
        payload = assemble_runtime_summary(watch_probe=_connected_probe, inbox_fetcher=lambda: None)

        self.assertEqual(_CANONICAL_TOP_LEVEL_KEYS, set(payload))
        self.assertEqual([], payload["active_runs"])
        self.assertEqual(0, payload["approvals"]["pending_count"])
        self.assertEqual([], payload["signals"]["top_items"])

    def test_assembler_marks_degraded_when_watch_probe_fails(self) -> None:
        payload = assemble_runtime_summary(watch_probe=_disconnected_probe, inbox_fetcher=lambda: None)

        self.assertFalse(payload["watch"]["connected"])
        self.assertTrue(payload["degraded"]["active"])
        self.assertIn("watch probe failed", payload["degraded"]["reasons"])
        self.assertFalse(payload["capabilities"]["watch_connected"])

    def test_assembler_reflects_connected_watch_in_capabilities(self) -> None:
        payload = assemble_runtime_summary(watch_probe=_connected_probe, inbox_fetcher=lambda: None)

        self.assertTrue(payload["watch"]["connected"])
        self.assertFalse(payload["degraded"]["active"])
        self.assertTrue(payload["capabilities"]["watch_connected"])

    def test_assembler_populates_signals_from_watch_inbox(self) -> None:
        bootstrap_item = {
            "signal_id": "signal_watch_bootstrap_ready",
            "workspace_id": "workspace_bootstrap",
            "title": "Watch bootstrap ready",
            "summary": "Watch bootstrap signal is available.",
            "severity": "info",
            "status": "open",
            "source": "watch",
            "updated_at": "2026-07-03T16:00:00Z",
            "action_type": "open_dashboard",
        }
        watch_item = {
            "signal_id": "signal_monitor_dashpro_storage",
            "workspace_id": "workspace_dashpro",
            "title": "DashPro storage probe failed",
            "summary": "Child-project monitor reported a storage failure.",
            "severity": "high",
            "status": "open",
            "source": "watch",
            "updated_at": "2026-07-03T16:00:00Z",
            "action_type": "open_dashboard",
            "meta": {"signal_family": "child_project_monitor"},
        }
        watch_inbox = {
            "items": [bootstrap_item, watch_item],
            "count": 2,
            "updated_at": "2026-07-03T16:00:00Z",
        }
        payload = assemble_runtime_summary(
            watch_probe=_connected_probe,
            inbox_fetcher=lambda: watch_inbox,
        )

        # Bootstrap noise is filtered; actionable monitor signals remain.
        self.assertEqual(1, payload["signals"]["open_count"])
        self.assertEqual(watch_item["signal_id"], payload["signals"]["top_items"][0]["signal_id"])
        self.assertEqual(watch_item["severity"], payload["signals"]["top_items"][0]["severity"])
        self.assertEqual(watch_item["status"], payload["signals"]["top_items"][0]["status"])
        self.assertEqual(watch_item["source"], payload["signals"]["top_items"][0]["source"])

    def test_assembler_projects_pending_approval_count_from_runs(self) -> None:
        create_run(
            workspace_id="workspace_alpha",
            mode="agent",
            summary="Awaiting approval run",
            requires_approval=True,
        )

        payload = assemble_runtime_summary(
            watch_probe=_connected_probe,
            inbox_fetcher=lambda: None,
        )

        self.assertEqual(1, payload["approvals"]["pending_count"])
        self.assertIsNotNone(payload["approvals"]["latest_approval_at"])

    def test_assembled_payload_fits_runtime_summary_size_budget(self) -> None:
        payload = assemble_runtime_summary(watch_probe=_connected_probe, inbox_fetcher=lambda: None)
        encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        threshold = int(load_config()["dto_sizes"]["runtime_summary"]["threshold_bytes"])

        self.assertLessEqual(len(encoded), threshold)


if __name__ == "__main__":
    unittest.main()
