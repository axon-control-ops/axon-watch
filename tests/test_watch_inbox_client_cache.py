"""Control-plane watch inbox SWR / single-flight cache."""

from __future__ import annotations

import threading
import time
import unittest
from unittest.mock import patch

from app.adapters import watch_client


class WatchInboxClientCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        watch_client.reset_watch_inbox_cache()

    def tearDown(self) -> None:
        watch_client.reset_watch_inbox_cache()

    def test_cached_only_returns_immediately_without_blocking(self) -> None:
        started = threading.Event()

        def _slow_fetch(timeout_seconds: float) -> dict[str, object] | None:
            started.set()
            time.sleep(0.5)
            return {"items": [], "count": 0, "updated_at": "bg"}

        with patch.object(watch_client, "_fetch_watch_inbox_uncached", side_effect=_slow_fetch):
            t0 = time.time()
            payload = watch_client.fetch_watch_inbox(cached_only=True)
            elapsed = time.time() - t0
        self.assertIsNone(payload)
        self.assertLess(elapsed, 0.2)
        # Background warm may start, but the caller must not wait for it.
        started.wait(0.2)
    def test_fresh_cache_hit_skips_live_probe(self) -> None:
        seed = {"items": [{"signal_id": "sig_1"}], "count": 1, "updated_at": "t"}
        watch_client._store_watch_inbox_cache(seed)
        with patch.object(
            watch_client,
            "_fetch_watch_inbox_uncached",
            side_effect=AssertionError("live probe must not run"),
        ) as live:
            payload = watch_client.fetch_watch_inbox()
        self.assertEqual(payload, seed)
        live.assert_not_called()

    def test_stale_cache_served_while_refresh_scheduled(self) -> None:
        seed = {"items": [], "count": 0, "updated_at": "stale"}
        watch_client._store_watch_inbox_cache(seed)
        # Expire TTL without clearing payload.
        with watch_client._INBOX_CACHE_LOCK:
            watch_client._INBOX_CACHE["fetched_at"] = time.monotonic() - 60.0

        refreshed = {"items": [{"signal_id": "sig_2"}], "count": 1, "updated_at": "fresh"}
        refresh_started = threading.Event()

        def _slow_refresh(timeout_seconds: float) -> dict[str, object] | None:
            refresh_started.set()
            time.sleep(0.05)
            return refreshed

        with patch.object(watch_client, "_fetch_watch_inbox_uncached", side_effect=_slow_refresh):
            first = watch_client.fetch_watch_inbox(allow_stale=True)
            self.assertEqual(first, seed)
            self.assertTrue(refresh_started.wait(1.0))
            # Wait for background refresh to publish.
            deadline = time.time() + 1.0
            while time.time() < deadline:
                _, cached = watch_client._read_watch_inbox_cache()
                if cached == refreshed:
                    break
                time.sleep(0.01)
            _, cached = watch_client._read_watch_inbox_cache()
            self.assertEqual(cached, refreshed)

    def test_single_flight_coalesces_cold_fetch(self) -> None:
        calls = {"n": 0}
        gate = threading.Event()
        release = threading.Event()

        def _slow_fetch(timeout_seconds: float) -> dict[str, object] | None:
            calls["n"] += 1
            gate.set()
            release.wait(1.0)
            return {"items": [], "count": 0, "updated_at": "live"}

        results: list[dict[str, object] | None] = []

        def _caller() -> None:
            results.append(watch_client.fetch_watch_inbox(allow_stale=False))

        with patch.object(watch_client, "_fetch_watch_inbox_uncached", side_effect=_slow_fetch):
            threads = [threading.Thread(target=_caller) for _ in range(4)]
            for thread in threads:
                thread.start()
            self.assertTrue(gate.wait(1.0))
            release.set()
            for thread in threads:
                thread.join(1.0)

        self.assertEqual(calls["n"], 1)
        self.assertEqual(len(results), 4)
        self.assertTrue(all(row == {"items": [], "count": 0, "updated_at": "live"} for row in results))


if __name__ == "__main__":
    unittest.main()
