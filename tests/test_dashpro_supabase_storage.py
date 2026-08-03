"""Tests for DashPro Supabase storage quota monitor."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

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

    def _patch_request(self, handler):
        def fake_request(request, *, timeout, retries):
            return handler(request)

        return patch.object(
            self.dashpro_supabase_storage,
            "_request_with_retries",
            side_effect=fake_request,
        )

    def test_storage_quota_critical_when_over_ninety_percent(self) -> None:
        rows = [{"bucket_id": "tts-audio", "object_count": 10, "total_bytes": 980_000_000}]

        def handler(request):
            url = request.full_url
            if "/storage/v1/bucket" in url:
                return 200, json.dumps([])
            if "/rpc/monitor_storage_bucket_usage" in url:
                return 200, json.dumps(rows)
            raise AssertionError(url)

        with self._patch_request(handler):
            status, detail = self.dashpro_supabase_storage.check_supabase_storage_quota(
                env={
                    "EXPO_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                }
            )

        self.assertEqual("critical", status)
        self.assertIn("tts-audio", detail)

    def test_storage_quota_warning_when_over_eighty_percent(self) -> None:
        rows = [
            {
                "bucket_id": "tts-audio",
                "object_count": 10,
                "total_bytes": int(1_073_741_824 * 0.85),
            }
        ]

        def handler(request):
            url = request.full_url
            if "/storage/v1/bucket" in url:
                return 200, json.dumps([])
            if "/rpc/monitor_storage_bucket_usage" in url:
                return 200, json.dumps(rows)
            raise AssertionError(url)

        with self._patch_request(handler):
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
        def handler(request):
            if "/storage/v1/bucket" in request.full_url:
                return 402, '{"error":"exceed_storage_size_quota"}'
            raise AssertionError(request.full_url)

        with self._patch_request(handler):
            status, detail = self.dashpro_supabase_storage.check_supabase_storage_quota(
                env={
                    "EXPO_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                }
            )

        self.assertEqual("critical", status)
        self.assertIn("402", detail)

    def test_transport_failure_downgrades_to_warning(self) -> None:
        def handler(request):
            raise TimeoutError("The read operation timed out")

        with self._patch_request(handler):
            status, detail = self.dashpro_supabase_storage.check_supabase_storage_quota(
                env={
                    "EXPO_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                },
                retries=0,
            )

        self.assertEqual("warning", status)
        self.assertIn("Supabase Storage API query failed", detail)

    def test_transport_failure_maps_to_warning_inbox_severity(self) -> None:
        from app.signals.monitor_signal import monitor_inbox_item  # noqa: WPS433

        def handler(request):
            raise TimeoutError("The read operation timed out")

        with self._patch_request(handler):
            status, detail = self.dashpro_supabase_storage.check_supabase_storage_quota(
                env={
                    "EXPO_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                },
                retries=0,
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
        def handler(request):
            url = request.full_url
            if "/storage/v1/bucket" in url:
                return 200, json.dumps([{"id": "tts-audio"}])
            if "/rpc/monitor_storage_bucket_usage" in url:
                return 404, '{"code":"PGRST202"}'
            if "/rest/v1/objects" in url:
                return 406, '{"message":"The schema must be one of the following: public, graphql_public"}'
            if "/storage/v1/object/list/tts-audio" in url:
                return 200, json.dumps(
                    [{"id": "file_1", "name": "clip.mp3", "metadata": {"size": 980_000_000}}]
                )
            raise AssertionError(url)

        with self._patch_request(handler):
            status, detail = self.dashpro_supabase_storage.check_supabase_storage_quota(
                env={
                    "EXPO_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                }
            )

        self.assertEqual("critical", status)
        self.assertIn("tts-audio", detail)

    def test_connection_reset_on_early_probe_falls_through_to_rpc(self) -> None:
        rows = [{"bucket_id": "tts-audio", "object_count": 1, "total_bytes": 100_000_000}]
        calls = {"storage_bucket": 0}

        def handler(request):
            url = request.full_url
            if "/storage/v1/bucket" in url:
                calls["storage_bucket"] += 1
                raise URLError("[Errno 104] Connection reset by peer")
            if "/rpc/monitor_storage_bucket_usage" in url:
                return 200, json.dumps(rows)
            raise AssertionError(url)

        with self._patch_request(handler):
            status, detail = self.dashpro_supabase_storage.check_supabase_storage_quota(
                env={
                    "EXPO_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                },
                retries=2,
            )

        self.assertEqual("ok", status)
        self.assertIn("tts-audio", detail)
        self.assertGreaterEqual(calls["storage_bucket"], 1)

    def test_connection_reset_retries_before_warning(self) -> None:
        attempts = {"count": 0}

        def fake_urlopen_with_retries(request, *, timeout, retries, backoff_seconds=0.5, read_response=None):
            attempts["count"] += 1
            url = request.full_url
            if "/storage/v1/bucket" in url:
                return 200, "[]"
            raise URLError("[Errno 104] Connection reset by peer")

        with patch.object(
            self.dashpro_supabase_storage,
            "urlopen_with_retries",
            side_effect=fake_urlopen_with_retries,
        ):
            status, detail = self.dashpro_supabase_storage.check_supabase_storage_quota(
                env={
                    "EXPO_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                },
                retries=2,
            )

        self.assertEqual("warning", status)
        self.assertIn("Supabase Storage API query failed", detail)
        self.assertIn("after 3 attempts", detail)
        # Early probe succeeds once; RPC path is attempted after transient fall-through.
        self.assertGreaterEqual(attempts["count"], 2)


if __name__ == "__main__":
    unittest.main()
