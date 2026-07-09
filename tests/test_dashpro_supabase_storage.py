"""Tests for DashPro Supabase storage quota monitor."""

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

import app.monitors.dashpro_supabase_storage as dashpro_supabase_storage  # noqa: E402


class DashProSupabaseStorageMonitorTests(unittest.TestCase):
    def test_storage_quota_critical_when_over_ninety_percent(self) -> None:
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

        rows = [{"bucket_id": "tts-audio", "object_count": 10, "total_bytes": 980_000_000}]

        def fake_urlopen(req, timeout=0):
            if "/storage/v1/bucket" in req.full_url:
                return _FakeResponse(200, [])
            if "/rpc/monitor_storage_bucket_usage" in req.full_url:
                return _FakeResponse(200, rows)
            raise AssertionError(req.full_url)

        with patch.object(dashpro_supabase_storage, "urlopen", side_effect=fake_urlopen):
            status, detail = dashpro_supabase_storage.check_supabase_storage_quota(
                env={
                    "EXPO_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                }
            )

        self.assertEqual("critical", status)
        self.assertIn("tts-audio", detail)

    def test_storage_quota_skipped_without_credentials(self) -> None:
        status, detail = dashpro_supabase_storage.check_supabase_storage_quota(env={})
        self.assertEqual("skipped", status)
        self.assertIn("service-role", detail)

    def test_storage_quota_flags_402_restriction(self) -> None:
        def fake_urlopen(req, timeout=0):
            if "/storage/v1/bucket" in req.full_url:
                raise HTTPError(
                    req.full_url,
                    402,
                    "Payment Required",
                    hdrs=None,
                    fp=type(
                        "Body",
                        (),
                        {
                            "read": lambda self: b'{"error":"exceed_storage_size_quota"}',
                            "close": lambda self: None,
                        },
                    )(),
                )
            raise AssertionError(req.full_url)

        with patch.object(dashpro_supabase_storage, "urlopen", side_effect=fake_urlopen):
            status, detail = dashpro_supabase_storage.check_supabase_storage_quota(
                env={
                    "EXPO_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                }
            )

        self.assertEqual("critical", status)
        self.assertIn("402", detail)

    def test_storage_quota_falls_back_to_storage_api_when_storage_schema_is_blocked(self) -> None:
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
            url = req.full_url
            if "/storage/v1/bucket" in url:
                return _FakeResponse(200, [{"id": "tts-audio"}])
            if "/rpc/monitor_storage_bucket_usage" in url:
                raise HTTPError(
                    url,
                    404,
                    "Not Found",
                    hdrs=None,
                    fp=type(
                        "Body",
                        (),
                        {"read": lambda self: b'{"code":"PGRST202"}', "close": lambda self: None},
                    )(),
                )
            if "/rest/v1/objects" in url:
                raise HTTPError(
                    url,
                    406,
                    "Not Acceptable",
                    hdrs=None,
                    fp=type(
                        "Body",
                        (),
                        {
                            "read": lambda self: b'{"message":"The schema must be one of the following: public, graphql_public"}',
                            "close": lambda self: None,
                        },
                    )(),
                )
            if "/storage/v1/object/list/tts-audio" in url:
                return _FakeResponse(
                    200,
                    [{"id": "file_1", "name": "clip.mp3", "metadata": {"size": 980_000_000}}],
                )
            raise AssertionError(url)

        with patch.object(dashpro_supabase_storage, "urlopen", side_effect=fake_urlopen):
            status, detail = dashpro_supabase_storage.check_supabase_storage_quota(
                env={
                    "EXPO_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                }
            )

        self.assertEqual("critical", status)
        self.assertIn("tts-audio", detail)


if __name__ == "__main__":
    unittest.main()
