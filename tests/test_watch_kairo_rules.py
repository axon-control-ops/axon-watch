from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from tests.support.watch_app_loader import load_watch_app, restore_app_modules
from tests.support.watch_db import isolate_watch_db


class WatchKairoRuleTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_watch_db(self)
        watch_app, self._watch_modules = load_watch_app()
        from app.delivery import store as delivery_store  # noqa: WPS433
        from app.events import store as event_store  # noqa: WPS433

        delivery_store.reset_store()
        event_store.reset_store()
        self.client = TestClient(watch_app)
        self.addCleanup(self.client.close)

    def tearDown(self) -> None:
        restore_app_modules(self._watch_modules)

    def _inbox_item(self, signal_id: str) -> dict[str, object]:
        response = self.client.get("/internal/watch/inbox")
        self.assertEqual(200, response.status_code)
        return next(row for row in response.json()["items"] if row["signal_id"] == signal_id)

    def test_summary_degraded_preserves_observe_watch_rule(self) -> None:
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
