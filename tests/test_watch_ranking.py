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
    from app.signals.ranking import (
        action_type_rank,
        rank_inbox_items,
        severity_rank,
        status_rank,
        unresolved_duration_key,
        workspace_priority_rank,
    )  # noqa: WPS433

    return (
        rank_inbox_items,
        severity_rank,
        status_rank,
        action_type_rank,
        workspace_priority_rank,
        unresolved_duration_key,
        cached,
    )


def _restore_modules(cached: dict[str, object]) -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    sys.modules.update(cached)


class WatchRankingTests(unittest.TestCase):
    def setUp(self) -> None:
        (
            self.rank_inbox_items,
            self.severity_rank,
            self.status_rank,
            self.action_type_rank,
            self.workspace_priority_rank,
            self.unresolved_duration_key,
            self._cached_modules,
        ) = _load_ranking_module()

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

    def test_status_rank_prefers_open_over_resolved(self) -> None:
        self.assertLess(self.status_rank("open"), self.status_rank("resolved"))

    def test_action_type_rank_prefers_approvals_over_dashboard(self) -> None:
        self.assertLess(self.action_type_rank("open_approvals"), self.action_type_rank("open_dashboard"))

    def test_workspace_priority_rank_prefers_configured_workspace(self) -> None:
        self.assertLess(
            self.workspace_priority_rank("workspace_bootstrap"),
            self.workspace_priority_rank("workspace_unknown"),
        )

    def test_rank_inbox_items_prefers_open_status_over_resolved_at_same_severity(self) -> None:
        resolved = {
            "signal_id": "signal_resolved",
            "severity": "warning",
            "status": "resolved",
            "updated_at": "2026-07-03T16:00:00Z",
            "action_type": "open_dashboard",
            "workspace_id": "workspace_alpha",
        }
        open_item = {
            "signal_id": "signal_open",
            "severity": "warning",
            "status": "open",
            "updated_at": "2026-07-03T15:00:00Z",
            "action_type": "open_dashboard",
            "workspace_id": "workspace_alpha",
        }

        ranked = self.rank_inbox_items([resolved, open_item])
        self.assertEqual("signal_open", ranked[0]["signal_id"])

    def test_rank_inbox_items_prefers_actionable_type_at_same_severity_and_status(self) -> None:
        passive = {
            "signal_id": "signal_passive",
            "severity": "warning",
            "status": "open",
            "updated_at": "2026-07-03T16:00:00Z",
            "action_type": "none",
            "workspace_id": "workspace_alpha",
        }
        actionable = {
            "signal_id": "signal_actionable",
            "severity": "warning",
            "status": "open",
            "updated_at": "2026-07-03T15:00:00Z",
            "action_type": "open_approvals",
            "workspace_id": "workspace_alpha",
        }

        ranked = self.rank_inbox_items([passive, actionable])
        self.assertEqual("signal_actionable", ranked[0]["signal_id"])

    def test_rank_inbox_items_prefers_higher_priority_workspace_when_other_keys_match(self) -> None:
        lower_priority = {
            "signal_id": "signal_other_workspace",
            "severity": "warning",
            "status": "open",
            "updated_at": "2026-07-03T16:00:00Z",
            "action_type": "open_dashboard",
            "workspace_id": "workspace_other",
        }
        higher_priority = {
            "signal_id": "signal_bootstrap_workspace",
            "severity": "warning",
            "status": "open",
            "updated_at": "2026-07-03T15:00:00Z",
            "action_type": "open_dashboard",
            "workspace_id": "workspace_bootstrap",
        }

        ranked = self.rank_inbox_items([lower_priority, higher_priority])
        self.assertEqual("signal_bootstrap_workspace", ranked[0]["signal_id"])

    def test_rank_inbox_items_prefers_longer_unresolved_duration_at_same_severity(self) -> None:
        newer_unresolved = {
            "signal_id": "signal_newer_unresolved",
            "severity": "warning",
            "status": "open",
            "created_at": "2026-07-03T12:00:00Z",
            "updated_at": "2026-07-03T16:00:00Z",
            "action_type": "open_dashboard",
            "workspace_id": "workspace_alpha",
        }
        older_unresolved = {
            "signal_id": "signal_older_unresolved",
            "severity": "warning",
            "status": "open",
            "created_at": "2026-07-03T08:00:00Z",
            "updated_at": "2026-07-03T16:00:00Z",
            "action_type": "open_dashboard",
            "workspace_id": "workspace_alpha",
        }

        ranked = self.rank_inbox_items([newer_unresolved, older_unresolved])
        self.assertEqual("signal_older_unresolved", ranked[0]["signal_id"])


if __name__ == "__main__":
    unittest.main()
