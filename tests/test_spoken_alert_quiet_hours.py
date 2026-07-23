"""Quiet hours / dedupe / escalation coverage for spoken alert policy."""

from __future__ import annotations

import unittest
from datetime import datetime

from app.spoken_alert_policy import (
    clear_spoken_alert_dedupe_for_tests,
    in_quiet_hours,
    resolve_spoken_alert,
)


class SpokenAlertPolicyQuietHoursTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_spoken_alert_dedupe_for_tests()

    def test_quiet_hours_overnight_window(self) -> None:
        settings = {"quiet_hours_start": "22:00", "quiet_hours_end": "07:00"}
        self.assertTrue(in_quiet_hours(settings, now=datetime(2026, 7, 22, 23, 0)))
        self.assertTrue(in_quiet_hours(settings, now=datetime(2026, 7, 22, 3, 0)))
        self.assertFalse(in_quiet_hours(settings, now=datetime(2026, 7, 22, 12, 0)))

    def test_quiet_hours_blocks_non_approval_signals(self) -> None:
        settings = {
            "operator_persona_enabled": True,
            "spoken_alerts_enabled": True,
            "privacy_mode": False,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "07:00",
        }
        payload = resolve_spoken_alert(
            settings=settings,
            pending_approvals=0,
            top_signal={
                "signal_id": "sig-1",
                "severity": "high",
                "title": "Degraded",
                "watch_rule": {"mode": "execute", "interrupts": True, "reason": "runtime_degraded"},
            },
            now=datetime(2026, 7, 22, 23, 30),
        )
        self.assertFalse(payload["eligible"])
        self.assertEqual(payload["reason"], "quiet_hours")

    def test_approvals_escalate_once_during_quiet_hours(self) -> None:
        settings = {
            "operator_persona_enabled": True,
            "spoken_alerts_enabled": True,
            "privacy_mode": False,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "07:00",
        }
        first = resolve_spoken_alert(
            settings=settings,
            pending_approvals=1,
            top_signal=None,
            now=datetime(2026, 7, 22, 23, 30),
            now_ts=1_000.0,
        )
        self.assertTrue(first["eligible"])
        second = resolve_spoken_alert(
            settings=settings,
            pending_approvals=1,
            top_signal=None,
            now=datetime(2026, 7, 22, 23, 31),
            now_ts=1_010.0,
        )
        self.assertFalse(second["eligible"])
        self.assertEqual(second["reason"], "duplicate_suppressed")

    def test_critical_can_speak_in_quiet_hours(self) -> None:
        settings = {
            "operator_persona_enabled": True,
            "spoken_alerts_enabled": True,
            "privacy_mode": False,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "07:00",
        }
        payload = resolve_spoken_alert(
            settings=settings,
            pending_approvals=0,
            top_signal={
                "signal_id": "sig-crit",
                "severity": "critical",
                "title": "Outage",
                "watch_rule": {"mode": "execute", "interrupts": True, "reason": "outage"},
            },
            now=datetime(2026, 7, 22, 23, 30),
            now_ts=2_000.0,
        )
        self.assertTrue(payload["eligible"])


if __name__ == "__main__":
    unittest.main()
