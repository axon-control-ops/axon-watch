"""Connector probe failure → inbox signal projection tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
_WATCH_PATH = str(WATCH_SERVICE_ROOT)


class ConnectorSignalTests(unittest.TestCase):
    connector_signal: object
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
        from app.signals import connector_signal as connector_signal_module  # noqa: WPS433

        self.connector_signal = connector_signal_module

    def tearDown(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        while _WATCH_PATH in sys.path:
            sys.path.remove(_WATCH_PATH)
        sys.modules.update(self._saved_modules)

    def test_ok_connector_emits_no_inbox_item(self) -> None:
        item = self.connector_signal.connector_inbox_item(
            {
                "connector_id": "control_plane",
                "display_name": "Control plane",
                "status": "ok",
                "required": True,
            }
        )
        self.assertIsNone(item)

    def test_optional_failure_emits_no_inbox_item(self) -> None:
        item = self.connector_signal.connector_inbox_item(
            {
                "connector_id": "axon_local",
                "display_name": "axon-local (legacy)",
                "status": "unavailable",
                "required": False,
                "detail": "connection refused",
            }
        )
        self.assertIsNone(item)

    def test_optional_tunnel_with_legacy_ingress_emits_investigate_signal(self) -> None:
        item = self.connector_signal.connector_inbox_item(
            {
                "connector_id": "cloudflare_tunnel",
                "display_name": "Cloudflare tunnel",
                "status": "degraded",
                "required": False,
                "detail": "ingress still targets legacy Axon Local",
                "tunnel": {"ingress_matches_axon": False},
            }
        )
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual("signal_connector_cloudflare_tunnel_degraded", item["signal_id"])
        self.assertEqual("high", item["severity"])
        self.assertEqual("investigate", item["action_type"])

    def test_optional_tunnel_with_axon_ingress_stays_out_of_inbox(self) -> None:
        item = self.connector_signal.connector_inbox_item(
            {
                "connector_id": "cloudflare_tunnel",
                "display_name": "Cloudflare tunnel",
                "status": "degraded",
                "required": False,
                "tunnel": {"ingress_matches_axon": True},
            }
        )
        self.assertIsNone(item)

    def test_required_degraded_emits_high_investigate_signal(self) -> None:
        item = self.connector_signal.connector_inbox_item(
            {
                "connector_id": "console_web",
                "display_name": "Console web",
                "status": "degraded",
                "required": True,
                "detail": "status=503",
                "workspace_id": "workspace_axon_watch",
            }
        )
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual("signal_connector_console_web_degraded", item["signal_id"])
        self.assertEqual("high", item["severity"])
        self.assertEqual("connector", item["source"])
        self.assertEqual("investigate", item["action_type"])
        self.assertEqual("status=503", item["summary"])
        self.assertEqual("workspace_axon_watch", item["workspace_id"])

    def test_required_unavailable_emits_critical_signal(self) -> None:
        item = self.connector_signal.connector_inbox_item(
            {
                "connector_id": "control_plane",
                "display_name": "Control plane",
                "status": "unavailable",
                "required": True,
            }
        )
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual("signal_connector_control_plane_unavailable", item["signal_id"])
        self.assertEqual("critical", item["severity"])
        self.assertIn("Control plane", item["title"])
        self.assertIn("unavailable", item["title"])

    def test_connector_inbox_items_filters_ok_and_optional(self) -> None:
        items = self.connector_signal.connector_inbox_items(
            [
                {
                    "connector_id": "control_plane",
                    "display_name": "Control plane",
                    "status": "ok",
                    "required": True,
                },
                {
                    "connector_id": "axon_local",
                    "display_name": "axon-local (legacy)",
                    "status": "unavailable",
                    "required": False,
                },
                {
                    "connector_id": "console_web",
                    "display_name": "Console web",
                    "status": "degraded",
                    "required": True,
                    "detail": "slow response",
                },
            ]
        )
        self.assertEqual(1, len(items))
        self.assertEqual("signal_connector_console_web_degraded", items[0]["signal_id"])


if __name__ == "__main__":
    unittest.main()
