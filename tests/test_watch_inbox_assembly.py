from __future__ import annotations

import unittest

from tests.support.watch_app_loader import prepare_watch_imports, restore_app_modules


class InboxAssemblyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._cached_modules = prepare_watch_imports()
        from app.signals.inbox_assembly import (  # noqa: WPS433
            connectors_trusted,
            include_summary_degraded_signal,
        )

        self.connectors_trusted = connectors_trusted
        self.include_summary_degraded_signal = include_summary_degraded_signal

    def tearDown(self) -> None:
        restore_app_modules(self._cached_modules)

    def test_connectors_trusted_when_required_all_ok(self) -> None:
        records = [
            {"connector_id": "control_plane", "required": True, "status": "ok"},
            {"connector_id": "console_web", "required": True, "status": "ok"},
            {"connector_id": "github_api", "required": False, "status": "unavailable"},
        ]
        self.assertTrue(self.connectors_trusted(records))

    def test_connectors_not_trusted_when_required_degraded(self) -> None:
        records = [
            {"connector_id": "control_plane", "required": True, "status": "ok"},
            {"connector_id": "console_web", "required": True, "status": "degraded"},
        ]
        self.assertFalse(self.connectors_trusted(records))

    def test_include_summary_degraded_when_connectors_untrusted(self) -> None:
        records = [
            {"connector_id": "control_plane", "required": True, "status": "ok"},
            {"connector_id": "console_web", "required": True, "status": "degraded"},
        ]
        self.assertTrue(self.include_summary_degraded_signal(connector_records=records))

    def test_omit_summary_degraded_when_connectors_trusted(self) -> None:
        records = [
            {"connector_id": "control_plane", "required": True, "status": "ok"},
            {"connector_id": "console_web", "required": True, "status": "ok"},
        ]
        self.assertFalse(self.include_summary_degraded_signal(connector_records=records))


if __name__ == "__main__":
    unittest.main()
