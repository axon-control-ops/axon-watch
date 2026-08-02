"""Tests for DashPro Sentry monitor check."""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
for module_name in list(sys.modules):
    if module_name == "app" or module_name.startswith("app."):
        sys.modules.pop(module_name, None)
sys.path.insert(0, str(WATCH_SERVICE_ROOT))

import app.monitors.dashpro_sentry as dashpro_sentry  # noqa: E402
import app.monitors.transport_retry as transport_retry  # noqa: E402


class DashProSentryMonitorTests(unittest.TestCase):
    def test_recent_issues_reports_unresolved_sample(self) -> None:
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

        issues = [
            {
                "id": "1",
                "shortId": "RN-1",
                "title": "TypeError: boom",
                "level": "error",
                "count": "4",
                "permalink": "https://sentry.io/issues/1/",
                "culprit": "app",
            }
        ]

        def fake_urlopen(req, timeout=0):
            self.assertEqual("GET", req.get_method())
            self.assertIn("/issues/", req.full_url)
            self.assertIn("environment%3Aproduction", req.full_url)
            self.assertIn("is%3Aunresolved", req.full_url)
            return _FakeResponse(200, issues)

        with patch.object(transport_retry, "urlopen", side_effect=fake_urlopen):
            status, detail, sample = dashpro_sentry.check_sentry_recent_issues(
                env={
                    "SENTRY_AUTH_TOKEN": "token",
                    "SENTRY_ORG_SLUG": "edudashpro",
                    "SENTRY_PROJECT_SLUG": "react-native",
                },
                warning_threshold=10,
                critical_threshold=20,
            )

        self.assertEqual("ok", status)
        self.assertIn("1 unresolved production issue(s)", detail)
        self.assertEqual(1, len(sample))

    def test_transport_failure_downgrades_to_warning(self) -> None:
        with patch.object(transport_retry, "urlopen",
            side_effect=TimeoutError("The read operation timed out"),
        ):
            status, detail, sample = dashpro_sentry.check_sentry_recent_issues(
                env={"SENTRY_AUTH_TOKEN": "token"},
                retries=0,
            )

        self.assertEqual("warning", status)
        self.assertIn("Sentry API query failed", detail)
        self.assertEqual([], sample)


    def test_transport_failure_retries_before_warning(self) -> None:
        calls = {"count": 0}

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
            calls["count"] += 1
            if calls["count"] == 1:
                raise TimeoutError("The read operation timed out")
            return _FakeResponse(200, [])

        with patch.object(transport_retry, "urlopen", side_effect=fake_urlopen):
            status, detail, sample = dashpro_sentry.check_sentry_recent_issues(
                env={"SENTRY_AUTH_TOKEN": "token"},
                retries=1,
            )

        self.assertEqual(2, calls["count"])
        self.assertEqual("ok", status)
        self.assertIn("zero unresolved production issues", detail)
        self.assertEqual([], sample)


    def test_dns_resolution_failure_retries_before_warning(self) -> None:
        calls = {"count": 0}

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
            calls["count"] += 1
            if calls["count"] == 1:
                raise OSError("[Errno -3] Temporary failure in name resolution")
            return _FakeResponse(200, [])

        with patch.object(transport_retry, "urlopen", side_effect=fake_urlopen):
            with patch.object(transport_retry, "time") as time_mock:
                status, detail, sample = dashpro_sentry.check_sentry_recent_issues(
                    env={"SENTRY_AUTH_TOKEN": "token"},
                    retries=2,
                )

        self.assertEqual(2, calls["count"])
        self.assertGreaterEqual(time_mock.sleep.call_count, 1)
        self.assertEqual("ok", status)
        self.assertIn("zero unresolved production issues", detail)
        self.assertEqual([], sample)

    def test_transport_failure_maps_to_warning_inbox_severity(self) -> None:
        from app.signals.monitor_signal import monitor_inbox_item  # noqa: WPS433

        with patch.object(transport_retry, "urlopen",
            side_effect=TimeoutError("The read operation timed out"),
        ):
            status, detail, _sample = dashpro_sentry.check_sentry_recent_issues(
                env={"SENTRY_AUTH_TOKEN": "token"},
                retries=0,
            )

        item = monitor_inbox_item(
            {
                "check_id": "dashpro_sentry_recent_issues",
                "check_type": "sentry_recent_issues",
                "service": "Sentry",
                "workspace_id": "workspace_dashpro",
                "workspace_label": "DashPro",
                "status": status,
                "detail": detail,
            }
        )
        assert item is not None
        self.assertEqual("warning", item["severity"])

    def test_attended_production_issue_is_suppressed(self) -> None:
        import tempfile
        from pathlib import Path

        from app.signals import sentry_issue_attendance_store

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

        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "watch.db")
            with patch.dict(os.environ, {"AXON_WATCH_WATCH_SERVICE_DB": db_path}):
                sentry_issue_attendance_store.reset_store()
                sentry_issue_attendance_store.attend_issue(
                    issue_id="1",
                    workspace_id="workspace_dashpro",
                    confirm_release="1.2.3",
                    attended_by="operator",
                )
                issues = [
                    {
                        "id": "1",
                        "shortId": "RN-1",
                        "title": "TypeError: boom",
                        "level": "error",
                        "count": "40",
                        "permalink": "https://sentry.io/issues/1/",
                        "culprit": "app",
                        "lastRelease": {"version": "1.2.3"},
                    }
                ]

                with patch.object(transport_retry, "urlopen",
                    return_value=_FakeResponse(200, issues),
                ):
                    status, detail, sample = dashpro_sentry.check_sentry_recent_issues(
                        env={"SENTRY_AUTH_TOKEN": "token"},
                        warning_threshold=1,
                        critical_threshold=2,
                    )

        self.assertEqual("ok", status)
        self.assertIn("suppressed", detail.lower())
        self.assertEqual([], sample)


if __name__ == "__main__":
    unittest.main()
