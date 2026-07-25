from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from urllib.error import URLError

from app.runs.service import create_run  # noqa: E402
from app.runtime_summary_assembler import assemble_runtime_summary, default_watch_probe  # noqa: E402

from scripts.verify.common import load_config  # noqa: E402
from tests.support.connector_signal_fixture import CONNECTOR_INBOX_ITEM, CONNECTOR_PROBE_DETAIL  # noqa: E402

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
        runtime_patch = patch(
            "app.runtime_summary_assembler.runtime_status_snapshot",
            return_value={
                "default_runtime": "cursor_local",
                "local": [
                    {
                        "id": "cursor_local",
                        "label": "Cursor CLI (local)",
                        "ready": True,
                        "available": True,
                        "auth": {"message": "Test runtime ready."},
                    }
                ],
            },
        )
        runtime_patch.start()
        self.addCleanup(runtime_patch.stop)

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

    def test_default_watch_probe_surfaces_connection_refused_detail(self) -> None:
        health_url = "http://127.0.0.1:8788/internal/watch/health"
        with patch(
            "app.runtime_summary_assembler.urlopen",
            side_effect=URLError("[Errno 111] Connection refused"),
        ), patch(
            "app.runtime_summary_assembler._watch_base_url",
            return_value="http://127.0.0.1:8788",
        ):
            connected, status, degraded_reason, _generated_at = default_watch_probe()

        self.assertFalse(connected)
        self.assertEqual("unavailable", status)
        self.assertEqual(f"Connection refused on {health_url}", degraded_reason)

    def test_assembler_reflects_connected_watch_in_capabilities(self) -> None:
        payload = assemble_runtime_summary(watch_probe=_connected_probe, inbox_fetcher=lambda: None)

        self.assertTrue(payload["watch"]["connected"])
        self.assertFalse(payload["degraded"]["active"])
        self.assertTrue(payload["capabilities"]["watch_connected"])

    def test_assembler_surfaces_connector_probe_detail_in_degraded_reasons(self) -> None:
        watch_inbox = {
            "items": [CONNECTOR_INBOX_ITEM],
            "count": 1,
            "updated_at": "2026-07-18T08:00:00Z",
        }
        watch_summary = {
            "connectors": {
                "configured": 2,
                "ok": 1,
                "degraded": 0,
                "unavailable": 1,
                "required_unavailable": 1,
            },
            "updated_at": "2026-07-18T08:00:00Z",
        }
        payload = assemble_runtime_summary(
            watch_probe=_connected_probe,
            inbox_fetcher=lambda: watch_inbox,
            watch_summary_fetcher=lambda: watch_summary,
        )

        self.assertTrue(payload["degraded"]["active"])
        self.assertEqual([CONNECTOR_PROBE_DETAIL], payload["degraded"]["reasons"])
        self.assertEqual(1, payload["connectors"]["required_unavailable"])

    def test_assembler_surfaces_degraded_required_connector_detail(self) -> None:
        watch_inbox = {
            "items": [
                {
                    "signal_id": "signal_connector_control_plane_degraded",
                    "workspace_id": "workspace_axon_watch",
                    "title": "Control plane connector degraded",
                    "summary": "HTTP 503",
                    "severity": "high",
                    "status": "open",
                    "source": "connector",
                    "updated_at": "2026-07-18T08:00:00Z",
                    "action_type": "investigate",
                }
            ],
            "count": 1,
            "updated_at": "2026-07-18T08:00:00Z",
        }
        watch_summary = {
            "connectors": {
                "configured": 2,
                "ok": 1,
                "degraded": 1,
                "unavailable": 0,
                "required_unavailable": 1,
            },
            "updated_at": "2026-07-18T08:00:00Z",
        }
        payload = assemble_runtime_summary(
            watch_probe=_connected_probe,
            inbox_fetcher=lambda: watch_inbox,
            watch_summary_fetcher=lambda: watch_summary,
        )

        self.assertTrue(payload["degraded"]["active"])
        self.assertEqual(["HTTP 503"], payload["degraded"]["reasons"])

    def test_assembler_surfaces_optional_tunnel_ingress_mismatch(self) -> None:
        tunnel_detail = (
            "tunnel stopped (auth=settings); remote ingress still points at "
            "http://localhost:7734; expected http://127.0.0.1:4173"
        )
        watch_inbox = {
            "items": [
                {
                    "signal_id": "signal_connector_cloudflare_tunnel_degraded",
                    "workspace_id": "workspace_axon_watch",
                    "title": "Cloudflare tunnel connector degraded",
                    "summary": tunnel_detail,
                    "severity": "high",
                    "status": "open",
                    "source": "connector",
                    "updated_at": "2026-07-18T08:00:00Z",
                    "action_type": "investigate",
                }
            ],
            "count": 1,
            "updated_at": "2026-07-18T08:00:00Z",
        }
        watch_summary = {
            "connectors": {
                "configured": 4,
                "ok": 2,
                "degraded": 1,
                "unavailable": 1,
                "required_unavailable": 0,
            },
            "updated_at": "2026-07-18T08:00:00Z",
        }
        payload = assemble_runtime_summary(
            watch_probe=_connected_probe,
            inbox_fetcher=lambda: watch_inbox,
            watch_summary_fetcher=lambda: watch_summary,
        )

        self.assertTrue(payload["degraded"]["active"])
        self.assertEqual([tunnel_detail], payload["degraded"]["reasons"])
        self.assertEqual(0, payload["connectors"]["required_unavailable"])

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
