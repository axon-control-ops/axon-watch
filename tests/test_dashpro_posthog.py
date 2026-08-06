from __future__ import annotations

import json
import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

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

    def test_timeout_retries_once_then_succeeds(self) -> None:
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

        calls = {"n": 0}

        def fake_urlopen(req, timeout=0):
            calls["n"] += 1
            self.assertEqual(20, timeout)
            if calls["n"] == 1:
                raise TimeoutError("The read operation timed out")
            return _FakeResponse(200, {"results": [{"event": "session_started"}]})

        with patch.object(dashpro_posthog, "urlopen", side_effect=fake_urlopen):
            status, detail = dashpro_posthog.check_posthog_recent_events(
                env={
                    "POSTHOG_PERSONAL_API_KEY": "phx_test",
                    "DASHPRO_POSTHOG_PROJECT_ID": "proj_123",
                },
                timeout_seconds=20,
                retries=1,
            )

        self.assertEqual(2, calls["n"])
        self.assertEqual("ok", status)
        self.assertIn("session_started", detail)

    def test_transport_failure_downgrades_to_warning(self) -> None:
        with patch.object(
            dashpro_posthog,
            "urlopen",
            side_effect=TimeoutError("The read operation timed out"),
        ):
            status, detail = dashpro_posthog.check_posthog_recent_events(
                env={
                    "POSTHOG_PERSONAL_API_KEY": "phx_test",
                    "DASHPRO_POSTHOG_PROJECT_ID": "proj_123",
                }
            )

        self.assertEqual("warning", status)
        self.assertIn("PostHog API query failed", detail)

    def test_transport_failure_maps_to_warning_inbox_severity(self) -> None:
        from app.signals.monitor_signal import monitor_inbox_item  # noqa: WPS433

        with patch.object(
            dashpro_posthog,
            "urlopen",
            side_effect=TimeoutError("The read operation timed out"),
        ):
            status, detail = dashpro_posthog.check_posthog_recent_events(
                env={
                    "POSTHOG_PERSONAL_API_KEY": "phx_test",
                    "DASHPRO_POSTHOG_PROJECT_ID": "proj_123",
                }
            )

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
        assert item is not None
        self.assertEqual("warning", item["severity"])

    def test_zero_events_maps_to_high_inbox_severity(self) -> None:
        from app.signals.monitor_signal import monitor_inbox_item  # noqa: WPS433

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

        with patch.object(
            dashpro_posthog,
            "urlopen",
            return_value=_FakeResponse(200, {"results": []}),
        ):
            status, detail = dashpro_posthog.check_posthog_recent_events(
                env={
                    "POSTHOG_PERSONAL_API_KEY": "phx_test",
                    "DASHPRO_POSTHOG_PROJECT_ID": "proj_123",
                }
            )

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
        assert item is not None
        self.assertEqual("warning", status)
        self.assertEqual("high", item["severity"])

    def test_upstream_503_downgrades_to_warning(self) -> None:
        def fake_urlopen(req, timeout=0):
            raise HTTPError(
                url=req.full_url,
                code=503,
                msg="Service Unavailable",
                hdrs=None,
                fp=BytesIO(b'{"detail":"Queries are a little too busy"}'),
            )

        with patch.object(dashpro_posthog, "urlopen", side_effect=fake_urlopen):
            status, detail = dashpro_posthog.check_posthog_recent_events(
                env={
                    "POSTHOG_PERSONAL_API_KEY": "phx_test",
                    "DASHPRO_POSTHOG_PROJECT_ID": "proj_123",
                }
            )

        self.assertEqual("warning", status)
        self.assertIn("HTTP 503", detail)


if __name__ == "__main__":
    unittest.main()
