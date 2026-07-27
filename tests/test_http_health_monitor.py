"""HTTP health monitor probe unit tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
_WATCH_PATH = str(WATCH_SERVICE_ROOT)


class HttpHealthMonitorTests(unittest.TestCase):
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
        import app.monitors.http_health as http_health  # noqa: WPS433
        import app.monitors.monitor_probe as monitor_probe  # noqa: WPS433

        self.http_health = http_health
        self.monitor_probe = monitor_probe

    def tearDown(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        while _WATCH_PATH in sys.path:
            sys.path.remove(_WATCH_PATH)
        sys.modules.update(self._saved_modules)

    def test_unresolved_placeholder_skipped(self) -> None:
        status, detail = self.http_health.check_http_health(
            url="${AXON_WATCH_PUBLIC_BASE_URL}/api/health"
        )
        self.assertEqual("skipped", status)
        self.assertIn("unresolved", detail)

    def test_missing_url_skipped(self) -> None:
        status, detail = self.http_health.check_http_health(url="")
        self.assertEqual("skipped", status)
        self.assertIn("url missing", detail)

    def test_ok_status(self) -> None:
        response = MagicMock()
        response.status = 200
        response.read.return_value = b'{"status":"ok"}'
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        with patch.object(self.http_health, "urlopen", return_value=response):
            status, detail = self.http_health.check_http_health(
                url="https://example.test/health",
                expect_json_status="ok",
            )
        self.assertEqual("ok", status)
        self.assertIn("reachable", detail)

    def test_probe_slice_http_health_only_without_project_root(self) -> None:
        with patch.object(
            self.monitor_probe,
            "check_http_health",
            return_value=("ok", "reachable (200)"),
        ):
            records = self.monitor_probe.probe_monitor_slice(
                {
                    "enabled": True,
                    "workspace_id": "workspace_axon_watch",
                    "workspace_label": "Axon-X",
                    "checks": [
                        {
                            "id": "public_health",
                            "type": "http_health",
                            "service": "Public origin",
                            "url": "https://axon.example/api/health",
                        }
                    ],
                }
            )
        self.assertEqual(1, len(records))
        self.assertEqual("http_health", records[0]["check_type"])
        self.assertEqual("ok", records[0]["status"])


if __name__ == "__main__":
    unittest.main()
