"""Tests for DashPro Supabase storage quota monitor."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
_WATCH_PATH = str(WATCH_SERVICE_ROOT)


class DashProSupabaseStorageMonitorTests(unittest.TestCase):
    dashpro_supabase_storage: object
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
        import app.monitors.dashpro_supabase_storage as dashpro_supabase_storage  # noqa: WPS433

        self.dashpro_supabase_storage = dashpro_supabase_storage

    def tearDown(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        while _WATCH_PATH in sys.path:
            sys.path.remove(_WATCH_PATH)
        sys.modules.update(self._saved_modules)

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

        with patch.object(self.dashpro_supabase_storage, "urlopen", side_effect=fake_urlopen):
            status, detail = self.dashpro_supabase_storage.check_supabase_storage_quota(
                env={
                    "EXPO_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                }
            )

        self.assertEqual("critical", status)
        self.assertIn("tts-audio", detail)

    def test_storage_quota_warning_when_over_eighty_percent(self) -> None:
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

        # 85% of the default 1 GiB quota (850M was only ~79% and returned ok).
        rows = [
            {
                "bucket_id": "tts-audio",
                "object_count": 10,
                "total_bytes": int(1_073_741_824 * 0.85),
            }
        ]

        def fake_urlopen(req, timeout=0):
            if "/storage/v1/bucket" in req.full_url:
                return _FakeResponse(200, [])
            if "/rpc/monitor_storage_bucket_usage" in req.full_url:
                return _FakeResponse(200, rows)
            raise AssertionError(req.full_url)

        with patch.object(self.dashpro_supabase_storage, "urlopen", side_effect=fake_urlopen):
            status, detail = self.dashpro_supabase_storage.check_supabase_storage_quota(
                env={
                    "EXPO_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                }
            )

        self.assertEqual("warning", status)
        self.assertIn("tts-audio", detail)
        self.assertIn("85%", detail)

    def test_storage_quota_skipped_without_credentials(self) -> None:
        status, detail = self.dashpro_supabase_storage.check_supabase_storage_quota(env={})
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

        with patch.object(self.dashpro_supabase_storage, "urlopen", side_effect=fake_urlopen):
            status, detail = self.dashpro_supabase_storage.check_supabase_storage_quota(
                env={
                    "EXPO_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                }
            )

        self.assertEqual("critical", status)
        self.assertIn("402", detail)

    def test_transport_failure_downgrades_to_warning(self) -> None:
        with patch.object(
            self.dashpro_supabase_storage,
            "urlopen",
            side_effect=TimeoutError("The read operation timed out"),
        ):
            status, detail = self.dashpro_supabase_storage.check_supabase_storage_quota(
                env={
                    "EXPO_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                }
            )

        self.assertEqual("warning", status)
        self.assertIn("Supabase Storage API query failed", detail)

    def test_transport_failure_maps_to_warning_inbox_severity(self) -> None:
        from app.signals.monitor_signal import monitor_inbox_item  # noqa: WPS433

        with patch.object(
            self.dashpro_supabase_storage,
            "urlopen",
            side_effect=TimeoutError("The read operation timed out"),
        ):
            status, detail = self.dashpro_supabase_storage.check_supabase_storage_quota(
                env={
                    "EXPO_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                }
            )

        item = monitor_inbox_item(
            {
                "check_id": "dashpro_supabase_storage_quota",
                "check_type": "supabase_storage_quota",
                "service": "Supabase Storage",
                "workspace_id": "workspace_dashpro",
                "workspace_label": "DashPro",
                "status": status,
                "detail": detail,
            }
        )
        assert item is not None
        self.assertEqual("warning", item["severity"])
        self.assertEqual(
            "signal_monitor_dashpro_supabase_storage_quota_warning",
            item["signal_id"],
        )

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

        with patch.object(self.dashpro_supabase_storage, "urlopen", side_effect=fake_urlopen):
            status, detail = self.dashpro_supabase_storage.check_supabase_storage_quota(
                env={
                    "EXPO_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                }
            )

        self.assertEqual("critical", status)
        self.assertIn("tts-audio", detail)


if __name__ == "__main__":
    unittest.main()
