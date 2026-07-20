from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from tests.support.stable_connector_probe import (
    patch_stable_connector_probes,
    reset_watch_ephemeral_stores,
)
from tests.support.watch_app_loader import load_watch_app, restore_app_modules
from tests.support.watch_db import isolate_watch_db


class WatchKairoRuleTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_watch_db(self)
        watch_app, self._watch_modules = load_watch_app()
        reset_watch_ephemeral_stores()
        self._connector_patch = patch_stable_connector_probes()
        self._connector_patch.start()
        self.addCleanup(self._connector_patch.stop)
        self.client = TestClient(watch_app)
        self.addCleanup(self.client.close)

    def tearDown(self) -> None:
        restore_app_modules(self._watch_modules)

    def _inbox_item(self, signal_id: str) -> dict[str, object]:
        response = self.client.get("/internal/watch/inbox")
        self.assertEqual(200, response.status_code)
        return next(row for row in response.json()["items"] if row["signal_id"] == signal_id)

    def test_summary_degraded_preserves_observe_watch_rule(self) -> None:
        from unittest.mock import patch

        from tests.support.stable_connector_probe import STABLE_OK_CONNECTOR_RECORDS

        degraded_connectors = [
            {
                **record,
                "status": "unavailable" if record.get("required") else record.get("status"),
            }
            for record in STABLE_OK_CONNECTOR_RECORDS
        ]
        with patch(
            "app.main.probe_all_connectors",
            return_value=degraded_connectors,
        ), patch(
            "app.connectors.summary.probe_all_connectors",
            return_value=degraded_connectors,
        ), patch(
            "app.watch_summary.probe_all_connectors",
            return_value=degraded_connectors,
        ):
            item = self._inbox_item("signal_runtime_summary_degraded")
        rule = item["watch_rule"]
        self.assertEqual("observe", rule["mode"])
        self.assertEqual("bootstrap_summary_stale", rule["reason"])
        self.assertFalse(rule["interrupts"])

    def test_bootstrap_signal_uses_observe_mode(self) -> None:
        item = self._inbox_item("signal_watch_bootstrap_ready")
        rule = item["watch_rule"]
        self.assertEqual("observe", rule["mode"])
        self.assertFalse(rule["interrupts"])

    def test_required_connector_failure_uses_advise_and_interrupts(self) -> None:
        from unittest.mock import patch

        probe_detail = "Connection refused on http://127.0.0.1:4173/api/health"
        connector_records = [
            {
                "connector_id": "control_plane",
                "display_name": "Control plane",
                "health_url": "http://127.0.0.1:8787/api/health",
                "required": True,
                "workspace_id": "workspace_axon_watch",
                "status": "ok",
                "detail": "ok",
                "last_checked_at": "2026-07-18T08:00:00Z",
                "latency_ms": 1,
            },
            {
                "connector_id": "console_web",
                "display_name": "Console web",
                "health_url": "http://127.0.0.1:4173/api/health",
                "required": True,
                "workspace_id": "workspace_axon_watch",
                "status": "unavailable",
                "detail": probe_detail,
                "last_checked_at": "2026-07-18T08:00:00Z",
                "latency_ms": 1,
            },
        ]
        with patch(
            "app.main.probe_all_connectors",
            return_value=connector_records,
        ), patch(
            "app.signals.store.probe_monitor_records",
            return_value=[],
        ):
            item = self._inbox_item("signal_connector_console_web_unavailable")

        rule = item["watch_rule"]
        self.assertEqual("advise", rule["mode"])
        self.assertEqual("high_urgency_signal", rule["reason"])
        self.assertTrue(rule["interrupts"])
        self.assertEqual(probe_detail, item["summary"])

    def test_watch_rule_modes_are_canonical(self) -> None:
        from app.signals.watch_rule import watch_rule_for_inbox_item  # noqa: WPS433

        approval = watch_rule_for_inbox_item(
            {"source": "approval", "severity": "high", "action_type": "open_approvals"}
        )
        self.assertEqual("approval", approval["mode"])
        self.assertTrue(approval["interrupts"])

        execute = watch_rule_for_inbox_item(
            {"source": "runtime", "severity": "critical", "action_type": "dispatch"}
        )
        self.assertEqual("execute", execute["mode"])
        self.assertTrue(execute["interrupts"])

        advise = watch_rule_for_inbox_item(
            {"source": "connector", "severity": "high", "action_type": "investigate"}
        )
        self.assertEqual("advise", advise["mode"])
        self.assertFalse(advise["interrupts"])

        observe = watch_rule_for_inbox_item(
            {"source": "watch", "severity": "info", "action_type": "none"}
        )
        self.assertEqual("observe", observe["mode"])
        self.assertFalse(observe["interrupts"])


if __name__ == "__main__":
    unittest.main()
