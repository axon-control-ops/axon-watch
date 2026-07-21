from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
_WATCH_PATH = str(WATCH_SERVICE_ROOT)


class DashProMonitorCacheTests(unittest.TestCase):
    dashpro_monitor: object
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
        import app.monitors.dashpro_monitor as dashpro_monitor  # noqa: WPS433

        self.dashpro_monitor = dashpro_monitor

    def tearDown(self) -> None:
        self.dashpro_monitor.reset_monitor_probe_cache()
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        while _WATCH_PATH in sys.path:
            sys.path.remove(_WATCH_PATH)
        sys.modules.update(self._saved_modules)

    def test_probe_monitor_records_reuses_recent_cached_results(self) -> None:
        with patch.object(
            self.dashpro_monitor,
            "probe_all_monitor_slices",
            return_value=[{"check_id": "dashpro_sentry_recent_issues", "status": "critical"}],
        ) as probe_mock:
            first = self.dashpro_monitor.probe_monitor_records()
            second = self.dashpro_monitor.probe_monitor_records()

        self.assertEqual(first, second)
        self.assertEqual(1, probe_mock.call_count)

    def test_reset_monitor_probe_cache_forces_refresh(self) -> None:
        with patch.object(
            self.dashpro_monitor,
            "probe_all_monitor_slices",
            side_effect=[
                [{"check_id": "first", "status": "warning"}],
                [{"check_id": "second", "status": "critical"}],
            ],
        ) as probe_mock:
            first = self.dashpro_monitor.probe_monitor_records()
            self.dashpro_monitor.reset_monitor_probe_cache()
            second = self.dashpro_monitor.probe_monitor_records()

        self.assertEqual([{"check_id": "first", "status": "warning"}], first)
        self.assertEqual([{"check_id": "second", "status": "critical"}], second)
        self.assertEqual(2, probe_mock.call_count)

    def test_cache_ttl_starts_after_probe_finishes(self) -> None:
        clock = {"value": 100.0}

        def _monotonic() -> float:
            return float(clock["value"])

        with patch.object(
            self.dashpro_monitor,
            "probe_all_monitor_slices",
            return_value=[{"check_id": "cached", "status": "critical"}],
        ) as probe_mock, patch.object(
            self.dashpro_monitor.time,
            "monotonic",
            side_effect=_monotonic,
        ):
            first = self.dashpro_monitor.probe_monitor_records()
            clock["value"] = 112.0
            second = self.dashpro_monitor.probe_monitor_records()

        self.assertEqual(first, second)
        self.assertEqual(1, probe_mock.call_count)

    def test_expired_cache_returns_stale_while_refreshing(self) -> None:
        import time as wall_time

        clock = {"value": 100.0}

        def _monotonic() -> float:
            return float(clock["value"])

        with patch.object(
            self.dashpro_monitor,
            "probe_all_monitor_slices",
            side_effect=[
                [{"check_id": "stale", "status": "warning"}],
                [{"check_id": "fresh", "status": "critical"}],
            ],
        ) as probe_mock, patch.object(
            self.dashpro_monitor.time,
            "monotonic",
            side_effect=_monotonic,
        ):
            first = self.dashpro_monitor.probe_monitor_records()
            clock["value"] = 200.0  # past 15s TTL
            second = self.dashpro_monitor.probe_monitor_records()
            # Allow background refresh to finish.
            deadline = wall_time.time() + 2.0
            while probe_mock.call_count < 2 and wall_time.time() < deadline:
                wall_time.sleep(0.01)

        self.assertEqual([{"check_id": "stale", "status": "warning"}], first)
        self.assertEqual([{"check_id": "stale", "status": "warning"}], second)
        self.assertGreaterEqual(probe_mock.call_count, 2)

    def test_execute_refresh_summary_clears_monitor_cache(self) -> None:
        from app.commands.executor import execute_refresh_summary

        with patch.object(
            self.dashpro_monitor,
            "probe_all_monitor_slices",
            side_effect=[
                [{"check_id": "cached", "status": "warning"}],
                [{"check_id": "fresh", "status": "critical"}],
            ],
        ) as probe_mock, patch(
            "app.connectors.summary.probe_all_connectors",
            return_value=[],
        ):
            self.dashpro_monitor.probe_monitor_records()
            execute_refresh_summary()
            result = self.dashpro_monitor.probe_monitor_records()

        self.assertEqual("fresh", result[0]["check_id"])
        self.assertEqual(2, probe_mock.call_count)


if __name__ == "__main__":
    unittest.main()
