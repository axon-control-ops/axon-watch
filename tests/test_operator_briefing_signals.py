"""Tests for actionable briefing signal filtering."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo_persona import build_persona_voice_line  # noqa: E402
from app.operator_briefing_signals import (  # noqa: E402
    first_actionable_signal,
    is_bootstrap_signal,
    is_monitor_signal,
    summarize_actionable_inbox,
)
from app.operator_presence import build_operator_presence  # noqa: E402


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

    def test_summarize_actionable_inbox(self) -> None:
        summary = summarize_actionable_inbox(
            [
                {
                    "signal_id": "signal_watch_bootstrap_ready",
                    "title": "Watch bootstrap ready",
                    "severity": "info",
                    "status": "open",
                },
                {
                    "signal_id": "signal_monitor_dashpro_sentry_recent_issues_critical",
                    "title": "DashPro Sentry critical",
                    "severity": "critical",
                    "status": "open",
                    "meta": {"signal_family": "child_project_monitor"},
                },
            ]
        )
        self.assertEqual(1, summary["open_count"])
        self.assertEqual(1, summary["critical_count"])

    def test_is_monitor_signal(self) -> None:
        self.assertTrue(
            is_monitor_signal(
                {
                    "signal_id": "signal_monitor_dashpro_sentry_recent_issues_critical",
                    "meta": {"signal_family": "child_project_monitor"},
                }
            )
        )
        self.assertFalse(
            is_monitor_signal(
                {
                    "signal_id": "signal_watch_bootstrap_ready",
                    "title": "Watch bootstrap ready",
                }
            )
        )

    def test_persona_uses_actionable_signal_title(self) -> None:
        line = build_persona_voice_line(
            pending_approvals=0,
            top_signal_title="Console web connector unavailable",
            top_signal_workspace_id="workspace_dashpro",
            top_signal_summary="Probe failed for console-web",
            degraded_active=False,
        )
        self.assertIn("connection Axon needs", line)
        self.assertTrue(line.startswith("VAXON:"))
        self.assertNotIn("Tell me which workspace to focus", line)

    def test_persona_signal_without_workspace_still_names_title(self) -> None:
        line = build_persona_voice_line(
            pending_approvals=0,
            top_signal_title="DashPro Sentry critical",
            degraded_active=False,
        )
        self.assertTrue(
            "DashPro" in line or "Sentry" in line or "connection" in line.lower(),
            line,
        )
        self.assertNotIn("Tell me which workspace to focus", line)


if __name__ == "__main__":
    unittest.main()
