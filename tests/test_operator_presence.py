from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo_persona import build_persona_voice_line  # noqa: E402
from app.operator_presence import build_operator_presence, resolve_presence_state  # noqa: E402
from app.spoken_alert_policy import resolve_spoken_alert  # noqa: E402


class OperatorPresencePolicyTests(unittest.TestCase):
    def test_spoken_alert_eligible_for_pending_approvals(self) -> None:
        payload = resolve_spoken_alert(
            settings={
                "operator_persona_enabled": True,
                "spoken_alerts_enabled": True,
                "privacy_mode": False,
                "mobile_compact_preferred": True,
            },
            pending_approvals=1,
            top_signal=None,
        )
        self.assertTrue(payload["eligible"])
        self.assertEqual("operator_approval_required", payload["reason"])
        self.assertIn("approval", payload["message"])

    def test_spoken_alert_blocked_by_privacy_mode(self) -> None:
        payload = resolve_spoken_alert(
            settings={
                "operator_persona_enabled": True,
                "spoken_alerts_enabled": True,
                "privacy_mode": True,
                "mobile_compact_preferred": True,
            },
            pending_approvals=1,
            top_signal=None,
        )
        self.assertFalse(payload["eligible"])
        self.assertEqual("privacy_mode_active", payload["reason"])

    def test_spoken_alert_eligible_for_interruptive_watch_rule(self) -> None:
        payload = resolve_spoken_alert(
            settings={
                "operator_persona_enabled": True,
                "spoken_alerts_enabled": True,
                "privacy_mode": False,
                "mobile_compact_preferred": True,
            },
            pending_approvals=0,
            top_signal={
                "signal_id": "signal_connector_console_web_unavailable",
                "title": "Console web connector unavailable",
                "severity": "critical",
                "watch_rule": {
                    "mode": "advise",
                    "reason": "high_urgency_signal",
                    "interrupts": True,
                },
            },
        )
        self.assertTrue(payload["eligible"])
        self.assertEqual("signal_connector_console_web_unavailable", payload["signal_id"])

    def test_persona_voice_line_for_degraded_runtime(self) -> None:
        line = build_persona_voice_line(
            pending_approvals=0,
            top_signal_title="",
            degraded_active=True,
        )
        self.assertIn("degraded", line.lower())

    def test_build_operator_presence_includes_mobile_foreground_only(self) -> None:
        payload = build_operator_presence(
            {
                "top_signals": [],
                "pending_approvals": {"count": 0},
                "degraded": {"active": False},
                "connectivity": {"watch_connected": True},
            },
            viewport_compact=True,
        )
        self.assertTrue(payload["mobile"]["foreground_only"])
        self.assertTrue(payload["mobile"]["compact_layout"])
        self.assertEqual("observing", payload["presence_state"])

    def test_presence_state_privacy_blocked(self) -> None:
        state = resolve_presence_state(
            settings={"privacy_mode": True},
            pending_approvals=0,
            critical_signals=0,
            high_signals=0,
            watch_connected=True,
            briefing_loaded=True,
        )
        self.assertEqual("privacy_blocked", state)


if __name__ == "__main__":
    unittest.main()
