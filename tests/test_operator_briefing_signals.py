"""Tests for actionable briefing signal filtering."""

from __future__ import annotations

import unittest

from app.operator_briefing_signals import first_actionable_signal, is_bootstrap_signal
from app.kairo_persona import build_persona_voice_line
from app.operator_presence import build_operator_presence


class OperatorBriefingSignalsTests(unittest.TestCase):
    def test_bootstrap_signal_detection(self) -> None:
        self.assertTrue(
            is_bootstrap_signal(
                {
                    "signal_id": "signal_watch_bootstrap_ready",
                    "title": "Watch bootstrap ready",
                    "severity": "info",
                }
            )
        )
        self.assertFalse(
            is_bootstrap_signal(
                {
                    "signal_id": "signal_connector_console_web_unavailable",
                    "title": "Console web connector unavailable",
                    "severity": "critical",
                }
            )
        )

    def test_persona_ignores_bootstrap_only_signal(self) -> None:
        presence = build_operator_presence(
            {
                "top_signals": [
                    {
                        "signal_id": "signal_watch_bootstrap_ready",
                        "title": "Watch bootstrap ready",
                        "severity": "info",
                    }
                ],
                "pending_approvals": {"count": 0},
                "degraded": {"active": False},
                "connectivity": {"watch_connected": True},
            }
        )
        self.assertIn("listening", presence["persona_voice_line"].lower())

    def test_first_actionable_signal_skips_bootstrap(self) -> None:
        signal = first_actionable_signal(
            [
                {
                    "signal_id": "signal_watch_bootstrap_ready",
                    "title": "Watch bootstrap ready",
                    "severity": "info",
                },
                {
                    "signal_id": "signal_connector_console_web_unavailable",
                    "title": "Console web connector unavailable",
                    "severity": "critical",
                },
            ]
        )
        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal["signal_id"], "signal_connector_console_web_unavailable")

    def test_persona_uses_actionable_signal_title(self) -> None:
        line = build_persona_voice_line(
            pending_approvals=0,
            top_signal_title="Console web connector unavailable",
            degraded_active=False,
        )
        self.assertIn("Top signals need review", line)


if __name__ == "__main__":
    unittest.main()
