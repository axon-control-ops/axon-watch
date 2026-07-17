from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
_WATCH_PATH = str(WATCH_SERVICE_ROOT)


class DashProSentryMonitorTests(unittest.TestCase):
    dashpro_sentry: object
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
        import app.monitors.dashpro_sentry as dashpro_sentry  # noqa: WPS433

        self.dashpro_sentry = dashpro_sentry

    def tearDown(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        while _WATCH_PATH in sys.path:
            sys.path.remove(_WATCH_PATH)
        sys.modules.update(self._saved_modules)

    def test_recent_issues_reports_unresolved_count(self) -> None:
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
            self.assertIn("/projects/edudashpro/react-native/issues/", req.full_url)
            return _FakeResponse(
                200,
                [
                    {
                        "id": "123",
                        "title": "TypeError: boom",
                        "count": 4,
                        "permalink": "https://sentry.io/issues/123/",
                    }
                ],
            )

        with patch.object(self.dashpro_sentry, "urlopen", side_effect=fake_urlopen):
            status, detail, issues = self.dashpro_sentry.check_sentry_recent_issues(
                env={"SENTRY_AUTH_TOKEN": "token", "SENTRY_ORG_SLUG": "edudashpro"}
            )

        self.assertEqual("ok", status)
        self.assertIn("1 unresolved issue(s)", detail)
        self.assertEqual(1, len(issues))

    def test_transport_failure_downgrades_to_warning(self) -> None:
        with patch.object(
            self.dashpro_sentry,
            "urlopen",
            side_effect=TimeoutError("The read operation timed out"),
        ):
            status, detail, issues = self.dashpro_sentry.check_sentry_recent_issues(
                env={"SENTRY_AUTH_TOKEN": "token", "SENTRY_ORG_SLUG": "edudashpro"}
            )

        self.assertEqual("warning", status)
        self.assertIn("Sentry API query failed", detail)
        self.assertEqual([], issues)


if __name__ == "__main__":
    unittest.main()
