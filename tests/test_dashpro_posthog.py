from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
for module_name in list(sys.modules):
    if module_name == "app" or module_name.startswith("app."):
        sys.modules.pop(module_name, None)
sys.path.insert(0, str(WATCH_SERVICE_ROOT))

import app.monitors.dashpro_posthog as dashpro_posthog  # noqa: E402


class DashProPostHogMonitorTests(unittest.TestCase):
    def test_recent_events_uses_events_endpoint_and_reports_latest_event(self) -> None:
        class _FakeResponse:
            def __init__(self, status: int, payload):
                self.status = status
                self._payload = payload

            def read(self):
                return json.dumps(self._payload).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_urlopen(req, timeout=0):
            self.assertEqual("GET", req.get_method())
            self.assertIn("/projects/proj_123/events/?limit=5", req.full_url)
            return _FakeResponse(
                200,
                {
                    "results": [
                        {"event": "dashboard_loaded"},
                        {"event": "message_opened"},
                    ]
                },
            )

        with patch.object(dashpro_posthog, "urlopen", side_effect=fake_urlopen):
            status, detail = dashpro_posthog.check_posthog_recent_events(
                env={
                    "POSTHOG_PERSONAL_API_KEY": "phx_test",
                    "DASHPRO_POSTHOG_PROJECT_ID": "proj_123",
                    "EXPO_PUBLIC_POSTHOG_HOST": "https://us.i.posthog.com",
                }
            )

        self.assertEqual("ok", status)
        self.assertIn("2 recent event(s)", detail)
        self.assertIn("dashboard_loaded", detail)


if __name__ == "__main__":
    unittest.main()
