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
        self.assertIn("latency_ms", record)


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


if __name__ == "__main__":
    unittest.main()
