from __future__ import annotations

import sys
import unittest
from pathlib import Path

WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"


def _load_ranking_module():
    cached = {
        name: module
        for name, module in sys.modules.items()
        if name == "app" or name.startswith("app.")
    }
    for name in cached:
        del sys.modules[name]

    sys.path.insert(0, str(WATCH_ROOT))
    from app.signals.ranking import rank_inbox_items, severity_rank  # noqa: WPS433

    return rank_inbox_items, severity_rank, cached


def _restore_modules(cached: dict[str, object]) -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    sys.modules.update(cached)


class WatchRankingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rank_inbox_items, self.severity_rank, self._cached_modules = _load_ranking_module()

    def tearDown(self) -> None:
        _restore_modules(self._cached_modules)

    def test_unknown_severity_sorts_after_known_severities(self) -> None:
        self.assertGreater(self.severity_rank("mystery"), self.severity_rank("info"))

    def test_rank_inbox_items_prefers_newer_item_within_same_severity(self) -> None:
        older = {
            "signal_id": "signal_older",
            "severity": "warning",
            "updated_at": "2026-07-03T15:00:00Z",
        }
        newer = {
            "signal_id": "signal_newer",
            "severity": "warning",
            "updated_at": "2026-07-03T16:00:00Z",
        }

        ranked = self.rank_inbox_items([older, newer])
        self.assertEqual("signal_newer", ranked[0]["signal_id"])
        self.assertEqual("signal_older", ranked[1]["signal_id"])

    def test_rank_inbox_items_prefers_higher_severity_over_recency(self) -> None:
        info_newer = {
            "signal_id": "signal_info_newer",
            "severity": "info",
            "updated_at": "2026-07-03T16:00:00Z",
        }
        high_older = {
            "signal_id": "signal_high_older",
            "severity": "high",
            "updated_at": "2026-07-03T15:00:00Z",
        }

        ranked = self.rank_inbox_items([info_newer, high_older])
        self.assertEqual("signal_high_older", ranked[0]["signal_id"])
        self.assertEqual("signal_info_newer", ranked[1]["signal_id"])


if __name__ == "__main__":
    unittest.main()
