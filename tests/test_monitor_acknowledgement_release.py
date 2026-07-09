from __future__ import annotations

import sys
import unittest
from pathlib import Path

WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
sys.path.insert(0, str(WATCH_ROOT))

from app.signals.suppression_store import (  # noqa: E402
    acknowledge_signals,
    is_signal_acknowledged,
    monitor_signal_ids_for_check,
    release_resolved_monitor_acknowledgements,
    reset_store,
)
from tests.support.watch_db import isolate_watch_db


class MonitorAcknowledgementReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_watch_db(self)
        reset_store()

    def test_release_resolved_monitor_acknowledgements_clears_suppression(self) -> None:
        signal_ids = monitor_signal_ids_for_check("dashpro_sentry_recent_issues")
        acknowledge_signals(signal_ids, acknowledged_by="operator")

        for signal_id in signal_ids:
            self.assertTrue(is_signal_acknowledged(signal_id))

        released = release_resolved_monitor_acknowledgements(
            [
                {
                    "check_id": "dashpro_sentry_recent_issues",
                    "status": "ok",
                }
            ],
        )

        self.assertEqual(signal_ids, released)
        for signal_id in signal_ids:
            self.assertFalse(is_signal_acknowledged(signal_id))

    def test_critical_monitor_records_do_not_release_acknowledgements(self) -> None:
        signal_ids = monitor_signal_ids_for_check("dashpro_sentry_recent_issues")
        acknowledge_signals(signal_ids, acknowledged_by="operator")

        released = release_resolved_monitor_acknowledgements(
            [
                {
                    "check_id": "dashpro_sentry_recent_issues",
                    "status": "critical",
                }
            ],
        )

        self.assertEqual([], released)
        for signal_id in signal_ids:
            self.assertTrue(is_signal_acknowledged(signal_id))


if __name__ == "__main__":
    unittest.main()
