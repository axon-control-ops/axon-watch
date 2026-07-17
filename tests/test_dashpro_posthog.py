from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
_WATCH_PATH = str(WATCH_SERVICE_ROOT)


class DashProPostHogMonitorTests(unittest.TestCase):
    dashpro_posthog: object
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
        import app.monitors.dashpro_posthog as dashpro_posthog  # noqa: WPS433

        self.dashpro_posthog = dashpro_posthog

    def tearDown(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        while _WATCH_PATH in sys.path:
            sys.path.remove(_WATCH_PATH)
        sys.modules.update(self._saved_modules)

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

        with patch.object(self.dashpro_posthog, "urlopen", side_effect=fake_urlopen):
            status, detail = self.dashpro_posthog.check_posthog_recent_events(
                env={
                    "POSTHOG_PERSONAL_API_KEY": "phx_test",
                    "DASHPRO_POSTHOG_PROJECT_ID": "proj_123",
                    "EXPO_PUBLIC_POSTHOG_HOST": "https://us.i.posthog.com",
                }
            )

        self.assertEqual("ok", status)
        self.assertIn("2 recent event(s)", detail)
        self.assertIn("dashboard_loaded", detail)

    def test_transport_failure_downgrades_to_warning(self) -> None:
        with patch.object(
            self.dashpro_posthog,
            "urlopen",
            side_effect=TimeoutError("The read operation timed out"),
        ):
            status, detail = self.dashpro_posthog.check_posthog_recent_events(
                env={
                    "POSTHOG_PERSONAL_API_KEY": "phx_test",
                    "DASHPRO_POSTHOG_PROJECT_ID": "proj_123",
                }
            )

        self.assertEqual("warning", status)
        self.assertIn("PostHog API query failed", detail)

    def test_auth_rejection_is_critical_status_and_critical_severity_inbox(self) -> None:
        from io import BytesIO  # noqa: WPS433
        from urllib.error import HTTPError  # noqa: WPS433

        def fake_urlopen(req, timeout=0):
            raise HTTPError(
                req.full_url,
                401,
                "Unauthorized",
                hdrs=None,
                fp=BytesIO(b'{"detail":"Invalid API key"}'),
            )

        with patch.object(self.dashpro_posthog, "urlopen", side_effect=fake_urlopen):
            status, detail = self.dashpro_posthog.check_posthog_recent_events(
                env={
                    "POSTHOG_PERSONAL_API_KEY": "phx_bad",
                    "DASHPRO_POSTHOG_PROJECT_ID": "proj_123",
                }
            )

        self.assertEqual("critical", status)
        self.assertIn("rejected the personal API key", detail)

        from app.signals.monitor_signal import monitor_inbox_item  # noqa: WPS433

        item = monitor_inbox_item(
            {
                "check_id": "dashpro_posthog_recent_events",
                "check_type": "posthog_recent_events",
                "service": "PostHog",
                "workspace_id": "workspace_dashpro",
                "workspace_label": "DashPro",
                "status": status,
                "detail": detail,
            }
        )
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual("critical", item["severity"])
        self.assertEqual(
            "signal_monitor_dashpro_posthog_recent_events_critical",
            item["signal_id"],
        )

    def test_zero_recent_events_downgrades_to_warning_status_but_high_severity_inbox(
        self,
    ) -> None:
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
            return _FakeResponse(200, {"results": []})

        with patch.object(self.dashpro_posthog, "urlopen", side_effect=fake_urlopen):
            status, detail = self.dashpro_posthog.check_posthog_recent_events(
                env={
                    "POSTHOG_PERSONAL_API_KEY": "phx_test",
                    "DASHPRO_POSTHOG_PROJECT_ID": "proj_123",
                }
            )

        self.assertEqual("warning", status)
        self.assertIn("zero recent events", detail)

        from app.signals.monitor_signal import monitor_inbox_item  # noqa: WPS433

        item = monitor_inbox_item(
            {
                "check_id": "dashpro_posthog_recent_events",
                "check_type": "posthog_recent_events",
                "service": "PostHog",
                "workspace_id": "workspace_dashpro",
                "workspace_label": "DashPro",
                "status": status,
                "detail": detail,
            }
        )
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual("high", item["severity"])


if __name__ == "__main__":
    unittest.main()
