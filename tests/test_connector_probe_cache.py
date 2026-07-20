from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
_WATCH_PATH = str(WATCH_SERVICE_ROOT)


class ConnectorProbeCacheTests(unittest.TestCase):
    connector_summary: object
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
        from app.connectors import summary as connector_summary  # noqa: WPS433

        self.connector_summary = connector_summary

    def tearDown(self) -> None:
        self.connector_summary.reset_connector_probe_cache()
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        while _WATCH_PATH in sys.path:
            sys.path.remove(_WATCH_PATH)
        sys.modules.update(self._saved_modules)

    def test_probe_all_connectors_reuses_recent_cached_results(self) -> None:
        with patch.object(
            self.connector_summary,
            "_probe_all_connectors_live",
            return_value=[
                {
                    "connector_id": "control_plane",
                    "status": "ok",
                    "required": True,
                }
            ],
        ) as probe_mock:
            first = self.connector_summary.probe_all_connectors()
            second = self.connector_summary.probe_all_connectors()

        self.assertEqual(first, second)
        self.assertEqual(1, probe_mock.call_count)

    def test_reset_connector_probe_cache_forces_refresh(self) -> None:
        with patch.object(
            self.connector_summary,
            "_probe_all_connectors_live",
            side_effect=[
                [{"connector_id": "control_plane", "status": "ok", "required": True}],
                [{"connector_id": "control_plane", "status": "degraded", "required": True}],
            ],
        ) as probe_mock:
            first = self.connector_summary.probe_all_connectors()
            self.connector_summary.reset_connector_probe_cache()
            second = self.connector_summary.probe_all_connectors()

        self.assertEqual("ok", first[0]["status"])
        self.assertEqual("degraded", second[0]["status"])
        self.assertEqual(2, probe_mock.call_count)

    def test_force_bypasses_cache(self) -> None:
        with patch.object(
            self.connector_summary,
            "_probe_all_connectors_live",
            side_effect=[
                [{"connector_id": "control_plane", "status": "ok", "required": True}],
                [{"connector_id": "control_plane", "status": "unavailable", "required": True}],
            ],
        ) as probe_mock:
            first = self.connector_summary.probe_all_connectors()
            second = self.connector_summary.probe_all_connectors(force=True)

        self.assertEqual("ok", first[0]["status"])
        self.assertEqual("unavailable", second[0]["status"])
        self.assertEqual(2, probe_mock.call_count)

    def test_store_connector_probe_record_seeds_cold_cache(self) -> None:
        with patch.object(
            self.connector_summary,
            "_probe_all_connectors_live",
            return_value=[
                {
                    "connector_id": "control_plane",
                    "status": "ok",
                    "required": True,
                    "detail": "reachable",
                },
                {
                    "connector_id": "console_web",
                    "status": "ok",
                    "required": True,
                    "detail": "reachable",
                },
            ],
        ) as live_mock:
            self.connector_summary.store_connector_probe_record(
                {
                    "connector_id": "control_plane",
                    "status": "degraded",
                    "required": True,
                    "detail": "status=degraded",
                }
            )
            cached = self.connector_summary.probe_all_connectors()

        self.assertEqual(1, live_mock.call_count)
        by_id = {str(item["connector_id"]): item for item in cached}
        self.assertEqual("degraded", by_id["control_plane"]["status"])
        self.assertEqual("ok", by_id["console_web"]["status"])

    def test_store_connector_probe_record_updates_warm_cache(self) -> None:
        with patch.object(
            self.connector_summary,
            "_probe_all_connectors_live",
            return_value=[
                {
                    "connector_id": "control_plane",
                    "status": "ok",
                    "required": True,
                    "detail": "reachable",
                },
                {
                    "connector_id": "console_web",
                    "status": "ok",
                    "required": True,
                    "detail": "reachable",
                },
            ],
        ) as probe_mock:
            self.connector_summary.probe_all_connectors()
            self.connector_summary.store_connector_probe_record(
                {
                    "connector_id": "control_plane",
                    "status": "degraded",
                    "required": True,
                    "detail": "status=degraded",
                }
            )
            cached = self.connector_summary.probe_all_connectors()

        self.assertEqual(1, probe_mock.call_count)
        by_id = {str(item["connector_id"]): item for item in cached}
        self.assertEqual("degraded", by_id["control_plane"]["status"])
        self.assertEqual("ok", by_id["console_web"]["status"])

    def test_cache_ttl_starts_after_probe_finishes(self) -> None:
        with patch.object(
            self.connector_summary,
            "_probe_all_connectors_live",
            return_value=[{"connector_id": "control_plane", "status": "ok", "required": True}],
        ) as probe_mock, patch.object(
            self.connector_summary.time,
            "monotonic",
            side_effect=[100.0, 112.0, 113.0],
        ):
            first = self.connector_summary.probe_all_connectors()
            second = self.connector_summary.probe_all_connectors()

        self.assertEqual(first, second)
        self.assertEqual(1, probe_mock.call_count)

    def test_execute_reprobe_connector_seeds_cold_cache(self) -> None:
        from app.commands.executor import execute_reprobe_connector
        from app.connectors.catalog import WatchConnectorDefinition

        definition = WatchConnectorDefinition(
            connector_id="control_plane",
            display_name="Control plane",
            health_url="http://127.0.0.1:8787/api/health",
            required=True,
            workspace_id="workspace_axon_watch",
        )

        with patch.object(
            self.connector_summary,
            "_probe_all_connectors_live",
            return_value=[
                {"connector_id": "control_plane", "status": "ok", "required": True},
                {"connector_id": "console_web", "status": "ok", "required": True},
            ],
        ) as live_mock, patch(
            "app.commands.executor.load_watch_connector_definitions",
            return_value={"control_plane": definition},
        ), patch(
            "app.commands.executor.probe_connector",
            return_value={
                "connector_id": "control_plane",
                "status": "degraded",
                "required": True,
                "detail": "status=degraded",
            },
        ):
            execute_reprobe_connector(connector_id="control_plane")
            cached = self.connector_summary.probe_all_connectors()

        self.assertEqual(1, live_mock.call_count)
        by_id = {str(item["connector_id"]): item for item in cached}
        self.assertEqual("degraded", by_id["control_plane"]["status"])
        self.assertEqual("ok", by_id["console_web"]["status"])

    def test_execute_reprobe_tunnel_seeds_cold_cache(self) -> None:
        from app.commands.executor import execute_reprobe_connector

        tunnel_config = {
            "enabled": True,
            "connector_id": "cloudflare_tunnel",
            "display_name": "Cloudflare tunnel",
        }

        with patch.object(
            self.connector_summary,
            "_probe_all_connectors_live",
            return_value=[
                {"connector_id": "control_plane", "status": "ok", "required": True},
                {"connector_id": "cloudflare_tunnel", "status": "ok", "required": True},
            ],
        ) as live_mock, patch(
            "app.commands.executor.load_watch_connector_definitions",
            return_value={},
        ), patch(
            "app.commands.executor.load_tunnel_slice",
            return_value=tunnel_config,
        ), patch(
            "app.commands.executor.probe_cloudflare_tunnel",
            return_value={
                "connector_id": "cloudflare_tunnel",
                "status": "degraded",
                "required": True,
                "detail": "soft cutover",
            },
        ):
            execute_reprobe_connector(connector_id="cloudflare_tunnel")
            cached = self.connector_summary.probe_all_connectors()

        self.assertEqual(1, live_mock.call_count)
        by_id = {str(item["connector_id"]): item for item in cached}
        self.assertEqual("degraded", by_id["cloudflare_tunnel"]["status"])
        self.assertEqual("ok", by_id["control_plane"]["status"])

    def test_execute_reprobe_connector_updates_warm_cache(self) -> None:
        from app.commands.executor import execute_reprobe_connector
        from app.connectors.catalog import WatchConnectorDefinition

        definition = WatchConnectorDefinition(
            connector_id="control_plane",
            display_name="Control plane",
            health_url="http://127.0.0.1:8787/api/health",
            required=True,
            workspace_id="workspace_axon_watch",
        )

        with patch.object(
            self.connector_summary,
            "_probe_all_connectors_live",
            return_value=[
                {"connector_id": "control_plane", "status": "ok", "required": True},
                {"connector_id": "console_web", "status": "ok", "required": True},
            ],
        ) as live_mock, patch(
            "app.commands.executor.load_watch_connector_definitions",
            return_value={"control_plane": definition},
        ), patch(
            "app.commands.executor.probe_connector",
            return_value={
                "connector_id": "control_plane",
                "status": "degraded",
                "required": True,
                "detail": "status=degraded",
            },
        ):
            self.connector_summary.probe_all_connectors()
            execute_reprobe_connector(connector_id="control_plane")
            cached = self.connector_summary.probe_all_connectors()

        self.assertEqual(1, live_mock.call_count)
        by_id = {str(item["connector_id"]): item for item in cached}
        self.assertEqual("degraded", by_id["control_plane"]["status"])
        self.assertEqual("ok", by_id["console_web"]["status"])

    def test_execute_reprobe_tunnel_updates_warm_cache(self) -> None:
        from app.commands.executor import execute_reprobe_connector

        tunnel_config = {
            "enabled": True,
            "connector_id": "cloudflare_tunnel",
            "display_name": "Cloudflare tunnel",
        }

        with patch.object(
            self.connector_summary,
            "_probe_all_connectors_live",
            return_value=[
                {"connector_id": "control_plane", "status": "ok", "required": True},
                {"connector_id": "cloudflare_tunnel", "status": "ok", "required": True},
            ],
        ) as live_mock, patch(
            "app.commands.executor.load_watch_connector_definitions",
            return_value={},
        ), patch(
            "app.commands.executor.load_tunnel_slice",
            return_value=tunnel_config,
        ), patch(
            "app.commands.executor.probe_cloudflare_tunnel",
            return_value={
                "connector_id": "cloudflare_tunnel",
                "status": "degraded",
                "required": True,
                "detail": "soft cutover",
            },
        ):
            self.connector_summary.probe_all_connectors()
            execute_reprobe_connector(connector_id="cloudflare_tunnel")
            cached = self.connector_summary.probe_all_connectors()

        self.assertEqual(1, live_mock.call_count)
        by_id = {str(item["connector_id"]): item for item in cached}
        self.assertEqual("degraded", by_id["cloudflare_tunnel"]["status"])
        self.assertEqual("ok", by_id["control_plane"]["status"])

    def test_execute_refresh_summary_clears_connector_cache(self) -> None:
        from app.commands.executor import execute_refresh_summary

        with patch.object(
            self.connector_summary,
            "_probe_all_connectors_live",
            side_effect=[
                [{"connector_id": "cached", "status": "ok", "required": True}],
                [{"connector_id": "fresh", "status": "degraded", "required": True}],
            ],
        ) as probe_mock, patch(
            "app.monitors.dashpro_monitor.probe_monitor_records",
            return_value=[],
        ):
            self.connector_summary.probe_all_connectors()
            execute_refresh_summary()
            result = self.connector_summary.probe_all_connectors()

        self.assertEqual("fresh", result[0]["connector_id"])
        self.assertEqual(2, probe_mock.call_count)


if __name__ == "__main__":
    unittest.main()
