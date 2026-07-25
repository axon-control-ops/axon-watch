"""Connector probe failures → assembled watch inbox snapshot tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
_WATCH_PATH = str(WATCH_ROOT)


class ConnectorInboxIntegrationTests(unittest.TestCase):
    get_inbox_snapshot: object
    summary_degraded_signal_id: str
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
        from tests.support.summary_degraded_signal_fixture import (  # noqa: WPS433
            SUMMARY_DEGRADED_SIGNAL_ID,
        )

        self.get_inbox_snapshot = get_inbox_snapshot
        self.summary_degraded_signal_id = SUMMARY_DEGRADED_SIGNAL_ID

    def tearDown(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        while _WATCH_PATH in sys.path:
            sys.path.remove(_WATCH_PATH)
        sys.modules.update(self._saved_modules)

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records", return_value=[])
    def test_required_degraded_connector_appears_in_inbox(
        self, _monitors, _email, _acked
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
                    "connector_id": "console_web",
                    "display_name": "Console web",
                    "status": "degraded",
                    "required": True,
                    "detail": "status=503",
                    "workspace_id": "workspace_axon_watch",
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
        connector_items = [
            item
            for item in payload["items"]
            if str(item.get("source")) == "connector"
        ]
        self.assertEqual(1, len(connector_items))
        self.assertEqual("high", connector_items[0]["severity"])
        self.assertEqual("investigate", connector_items[0]["action_type"])

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records", return_value=[])
    def test_soft_cutover_tunnel_stays_out_of_inbox(
        self, _monitors, _email, _acked
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
                    "detail": "active soft cutover (public=axon-x control-plane)",
                    "tunnel": {
                        "ingress_matches_axon": False,
                        "soft_origin_cutover": True,
                        "remote_ingress_service": "http://localhost:7734",
                    },
                },
            ]
        )
        signal_ids = [
            str(item.get("signal_id"))
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        self.assertFalse(any(signal_id.startswith("signal_connector_") for signal_id in signal_ids))

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records", return_value=[])
    def test_optional_connector_failure_stays_out_of_inbox(
        self, _monitors, _email, _acked
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
                    "connector_id": "console_web",
                    "display_name": "Console web",
                    "status": "ok",
                    "required": True,
                },
                {
                    "connector_id": "axon_local",
                    "display_name": "axon-local (legacy)",
                    "status": "unavailable",
                    "required": False,
                    "detail": "connection refused",
                },
            ]
        )
        signal_ids = [
            str(item.get("signal_id"))
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        self.assertFalse(any(signal_id.startswith("signal_connector_") for signal_id in signal_ids))
        self.assertNotIn(self.summary_degraded_signal_id, signal_ids)

    @patch("app.signals.store.is_signal_acknowledged", return_value=False)
    @patch("app.signals.store.email_inbox_items", return_value=[])
    @patch("app.signals.store.probe_monitor_records", return_value=[])
    def test_untrusted_required_connectors_keep_summary_degraded_and_connector_signal(
        self, _monitors, _email, _acked
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
        self.assertIn(self.summary_degraded_signal_id, signal_ids)
        self.assertIn("signal_connector_control_plane_unavailable", signal_ids)
        self.assertNotIn("signal_watch_bootstrap_ready", signal_ids)


if __name__ == "__main__":
    unittest.main()
