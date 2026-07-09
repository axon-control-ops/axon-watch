from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
for module_name in list(sys.modules):
    if module_name == "app" or module_name.startswith("app."):
        sys.modules.pop(module_name, None)
sys.path.insert(0, str(WATCH_SERVICE_ROOT))

import app.monitors.dashpro_monitor as dashpro_monitor  # noqa: E402


class DashProMonitorCacheTests(unittest.TestCase):
    def tearDown(self) -> None:
        dashpro_monitor.reset_monitor_probe_cache()

    def test_probe_monitor_records_reuses_recent_cached_results(self) -> None:
        with patch.object(
            dashpro_monitor,
            "probe_all_monitor_slices",
            return_value=[{"check_id": "dashpro_sentry_recent_issues", "status": "critical"}],
        ) as probe_mock:
            first = dashpro_monitor.probe_monitor_records()
            second = dashpro_monitor.probe_monitor_records()

        self.assertEqual(first, second)
        self.assertEqual(1, probe_mock.call_count)

    def test_reset_monitor_probe_cache_forces_refresh(self) -> None:
        with patch.object(
            dashpro_monitor,
            "probe_all_monitor_slices",
            side_effect=[
                [{"check_id": "first", "status": "warning"}],
                [{"check_id": "second", "status": "critical"}],
            ],
        ) as probe_mock:
            first = dashpro_monitor.probe_monitor_records()
            dashpro_monitor.reset_monitor_probe_cache()
            second = dashpro_monitor.probe_monitor_records()

        self.assertEqual([{"check_id": "first", "status": "warning"}], first)
        self.assertEqual([{"check_id": "second", "status": "critical"}], second)
        self.assertEqual(2, probe_mock.call_count)

    def test_cache_ttl_starts_after_probe_finishes(self) -> None:
        with patch.object(
            dashpro_monitor,
            "probe_all_monitor_slices",
            return_value=[{"check_id": "cached", "status": "critical"}],
        ) as probe_mock, patch.object(
            dashpro_monitor.time,
            "monotonic",
            side_effect=[100.0, 112.0, 113.0],
        ):
            first = dashpro_monitor.probe_monitor_records()
            second = dashpro_monitor.probe_monitor_records()

        self.assertEqual(first, second)
        self.assertEqual(1, probe_mock.call_count)


if __name__ == "__main__":
    unittest.main()
