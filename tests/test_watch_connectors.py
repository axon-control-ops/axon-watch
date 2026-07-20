from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.watch_app_loader import load_watch_app, restore_app_modules

WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"


class WatchConnectorCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        _watch_app, self._watch_modules = load_watch_app()
        from app.connectors import catalog as connector_catalog  # noqa: WPS433

        self.catalog = connector_catalog

    def tearDown(self) -> None:
        restore_app_modules(self._watch_modules)

    def test_loads_default_connectors_file(self) -> None:
        definitions = self.catalog.load_watch_connector_definitions()
        self.assertIn("control_plane", definitions)
        self.assertIn("console_web", definitions)
        self.assertTrue(definitions["control_plane"].required)

    def test_bootstrap_defaults_resolve_default_connectors_without_env(self) -> None:
        env_keys = (
            "AXON_WATCH_PUBLIC_BASE_URL",
            "AXON_WATCH_CONTROL_PLANE_BASE_URL",
            "AXON_WATCH_WATCH_SERVICE_BASE_URL",
            "AXON_WATCH_CONSOLE_WEB_PORT",
            "AXON_WATCH_CONTROL_PLANE_PORT",
            "AXON_WATCH_WATCH_SERVICE_PORT",
        )
        preserved = {key: os.environ.get(key) for key in env_keys}
        try:
            for key in env_keys:
                os.environ.pop(key, None)
            definitions = self.catalog.load_watch_connector_definitions()
        finally:
            for key, value in preserved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.assertEqual(
            "http://127.0.0.1:8787/api/health",
            definitions["control_plane"].health_url,
        )
        self.assertEqual(
            "http://127.0.0.1:4173/api/health",
            definitions["console_web"].health_url,
        )

    def test_expands_env_vars_in_health_url(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            connectors_file = Path(tempdir) / "connectors.json"
            connectors_file.write_text(
                json.dumps(
                    {
                        "connectors": {
                            "demo": {
                                "display_name": "Demo",
                                "health_url": "${AXON_WATCH_PROBE_DEMO_URL}/health",
                                "required": False,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"AXON_WATCH_PROBE_DEMO_URL": "http://127.0.0.1:9999"},
                clear=False,
            ):
                definitions = self.catalog.load_watch_connector_definitions(connectors_file)

        self.assertEqual("http://127.0.0.1:9999/health", definitions["demo"].health_url)


class WatchConnectorProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        _watch_app, self._watch_modules = load_watch_app()
        from app.connectors import catalog as connector_catalog  # noqa: WPS433
        from app.connectors import probe as connector_probe  # noqa: WPS433

        self.catalog = connector_catalog
        self.probe = connector_probe

    def tearDown(self) -> None:
        restore_app_modules(self._watch_modules)

    def test_probe_marks_unreachable_connector_unavailable(self) -> None:
        definition = self.catalog.WatchConnectorDefinition(
            connector_id="missing",
            display_name="Missing",
            health_url="http://127.0.0.1:1/unreachable",
            required=False,
            workspace_id="workspace_smoke",
        )
        record = self.probe.probe_connector(definition, timeout_seconds=0.2)
        self.assertEqual("unavailable", record["status"])
        self.assertEqual(
            "Connection refused on http://127.0.0.1:1/unreachable",
            record["detail"],
        )
        self.assertIn("latency_ms", record)

    def test_probe_formats_connection_refused_for_operator_detail(self) -> None:
        health_url = "http://127.0.0.1:1/unreachable"
        definition = self.catalog.WatchConnectorDefinition(
            connector_id="console_web",
            display_name="Console web",
            health_url=health_url,
            required=True,
            workspace_id="workspace_axon_watch",
        )
        record = self.probe.probe_connector(definition, timeout_seconds=0.2)

        self.assertEqual("unavailable", record["status"])
        self.assertEqual(f"Connection refused on {health_url}", record["detail"])

    def test_format_probe_failure_maps_timeout_and_dns_errors(self) -> None:
        from urllib.error import URLError

        from app.probe_failure_detail import format_probe_failure  # noqa: WPS433

        health_url = "http://127.0.0.1:4173/api/health"
        self.assertEqual(
            f"Timed out on {health_url}",
            format_probe_failure(TimeoutError("timed out"), health_url),
        )
        self.assertEqual(
            f"Timed out on {health_url}",
            format_probe_failure(URLError(TimeoutError("timed out")), health_url),
        )
        self.assertEqual(
            f"Host unreachable on {health_url}",
            format_probe_failure(
                OSError("[Errno -2] Name or service not known"),
                health_url,
            ),
        )
        self.assertEqual(
            f"Network unreachable on {health_url}",
            format_probe_failure(OSError(101, "Network is unreachable"), health_url),
        )
        self.assertEqual(
            f"Connection reset on {health_url}",
            format_probe_failure(URLError("[Errno 104] Connection reset by peer"), health_url),
        )
        self.assertEqual(
            f"TLS error on {health_url}",
            format_probe_failure(
                URLError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed"),
                health_url,
            ),
        )
        self.assertEqual(
            "probe failed",
            format_probe_failure(RuntimeError("unexpected"), health_url),
        )

    def test_unresolved_health_url_placeholder_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            connectors_file = Path(tempdir) / "connectors.json"
            connectors_file.write_text(
                json.dumps(
                    {
                        "connectors": {
                            "broken": {
                                "display_name": "Broken",
                                "health_url": "${AXON_WATCH_MISSING_PROBE_URL}/health",
                                "required": True,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(self.catalog.ConnectorConfigError) as ctx:
                self.catalog.load_watch_connector_definitions(connectors_file)

        self.assertIn("unresolved environment placeholders", str(ctx.exception))


class WatchConnectorApiTests(unittest.TestCase):
    def setUp(self) -> None:
        watch_app, self._watch_modules = load_watch_app()
        self.client = TestClient(watch_app)
        self.addCleanup(self.client.close)

    def tearDown(self) -> None:
        restore_app_modules(self._watch_modules)

    def test_connectors_endpoint_returns_probe_records(self) -> None:
        response = self.client.get("/internal/watch/connectors")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertGreaterEqual(payload["count"], 2)
        self.assertIn("summary", payload)
        items = payload["items"]
        self.assertTrue(any(item["connector_id"] == "control_plane" for item in items))

    def test_summary_endpoint_includes_connector_counts(self) -> None:
        response = self.client.get("/internal/watch/summary")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        connectors = payload["connectors"]
        self.assertGreaterEqual(connectors["configured"], 2)
        self.assertIn("ok", connectors)
        self.assertIn("required_unavailable", connectors)

    def test_inbox_surfaces_required_connector_probe_failure_detail(self) -> None:
        probe_detail = "Connection refused on http://127.0.0.1:4173/api/health"
        connector_records = [
            {
                "connector_id": "control_plane",
                "display_name": "Control plane",
                "health_url": "http://127.0.0.1:8787/api/health",
                "required": True,
                "workspace_id": "workspace_axon_watch",
                "status": "ok",
                "detail": "ok",
                "last_checked_at": "2026-07-18T08:00:00Z",
                "latency_ms": 1,
            },
            {
                "connector_id": "console_web",
                "display_name": "Console web",
                "health_url": "http://127.0.0.1:4173/api/health",
                "required": True,
                "workspace_id": "workspace_axon_watch",
                "status": "unavailable",
                "detail": probe_detail,
                "last_checked_at": "2026-07-18T08:00:00Z",
                "latency_ms": 1,
            },
        ]
        with patch("app.main.probe_all_connectors", return_value=connector_records), patch(
            "app.signals.store.probe_monitor_records",
            return_value=[],
        ):
            response = self.client.get("/internal/watch/inbox")

        self.assertEqual(200, response.status_code)
        connector_items = [
            item for item in response.json()["items"] if item.get("source") == "connector"
        ]
        self.assertEqual(1, len(connector_items))
        item = connector_items[0]
        self.assertEqual("signal_connector_console_web_unavailable", item["signal_id"])
        self.assertEqual(probe_detail, item["summary"])
        self.assertEqual("critical", item["severity"])


if __name__ == "__main__":
    unittest.main()
