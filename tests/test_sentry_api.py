"""Tests for Sentry write client (resolve + write-scope probe)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
for module_name in list(sys.modules):
    if module_name == "app" or module_name.startswith("app."):
        sys.modules.pop(module_name, None)
sys.path.insert(0, str(WATCH_SERVICE_ROOT))

import app.monitors.sentry_api as sentry_api  # noqa: E402


class _FakeResponse:
    def __init__(self, status: int, payload: object):
        self.status = status
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class SentryApiTests(unittest.TestCase):
    def test_resolve_requires_issue_id(self) -> None:
        result = sentry_api.resolve_sentry_issue("", env={"SENTRY_AUTH_TOKEN": "t", "SENTRY_ORG_SLUG": "org"})
        self.assertFalse(result["ok"])
        self.assertEqual("missing_issue_id", result["reason"])

    def test_resolve_requires_config(self) -> None:
        result = sentry_api.resolve_sentry_issue("123", env={})
        self.assertFalse(result["ok"])
        self.assertEqual("missing_config", result["reason"])

    def test_resolve_success(self) -> None:
        def fake_urlopen(req, timeout=0):
            self.assertIn("/issues/123/", req.full_url)
            self.assertEqual("PUT", req.get_method())
            return _FakeResponse(200, {"status": "resolved", "id": "123"})

        with patch.object(sentry_api, "urlopen", side_effect=fake_urlopen):
            result = sentry_api.resolve_sentry_issue(
                "123",
                env={"SENTRY_AUTH_TOKEN": "token", "SENTRY_ORG_SLUG": "edudashpro"},
            )
        self.assertTrue(result["ok"])
        self.assertEqual("resolved", result["status"])
        self.assertEqual("123", result["issue_id"])

    def test_resolve_missing_write_scope(self) -> None:
        def fake_urlopen(req, timeout=0):
            raise HTTPError(
                req.full_url,
                403,
                "Forbidden",
                hdrs=None,
                fp=type(
                    "Body",
                    (),
                    {"read": lambda self: b'{"detail":"no write"}', "close": lambda self: None},
                )(),
            )

        with patch.object(sentry_api, "urlopen", side_effect=fake_urlopen):
            result = sentry_api.resolve_sentry_issue(
                "123",
                env={"SENTRY_AUTH_TOKEN": "token", "SENTRY_ORG_SLUG": "edudashpro"},
            )
        self.assertFalse(result["ok"])
        self.assertEqual("missing_write_scope", result["reason"])

    def test_probe_write_scope_true_on_404(self) -> None:
        def fake_urlopen(req, timeout=0):
            raise HTTPError(
                req.full_url,
                404,
                "Not Found",
                hdrs=None,
                fp=type(
                    "Body",
                    (),
                    {"read": lambda self: b'{"detail":"not found"}', "close": lambda self: None},
                )(),
            )

        with patch.object(sentry_api, "urlopen", side_effect=fake_urlopen):
            result = sentry_api.probe_sentry_write_scope(
                env={"SENTRY_AUTH_TOKEN": "token", "SENTRY_ORG_SLUG": "edudashpro"}
            )
        self.assertTrue(result["ok"])
        self.assertTrue(result["write_scope"])


if __name__ == "__main__":
    unittest.main()
