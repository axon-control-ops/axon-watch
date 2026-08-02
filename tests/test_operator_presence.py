from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo_persona import build_persona_voice_line  # noqa: E402
from app.main import app  # noqa: E402
from app.operator_presence import build_operator_presence, resolve_presence_state  # noqa: E402
from app.persistence import operator_presence_settings_store, run_store  # noqa: E402
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
        self.assertIn("yes or no", payload["message"].lower())
        self.assertIsInstance(payload.get("explanation"), dict)
        self.assertIn("what", payload["explanation"])

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
        self.assertTrue(
            "weaker" in line.lower() or "degraded" in line.lower() or "look" in line.lower()
        )

    def test_persona_voice_line_neutral_when_persona_disabled(self) -> None:
        line = build_persona_voice_line(
            pending_approvals=2,
            top_signal_title="",
            degraded_active=False,
            persona_enabled=False,
        )
        self.assertNotIn("KAIRO", line)
        self.assertNotIn("VAXON", line)
        self.assertIn("yes or no", line.lower())

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

    def test_semi_autonomy_emits_advisory_without_interruptive_signal(self) -> None:
        payload = build_operator_presence(
            {
                "top_signals": [],
                "pending_approvals": {"count": 0},
                "degraded": {"active": False},
                "connectivity": {"watch_connected": True},
                "notice": "Fleet quiet.",
                "advise": "Watch DashPro CI and keep Leads on cooldown.",
                "production_readiness": {
                    "score": 75,
                    "grade": "partial",
                    "summary": "Production readiness 75/100 (partial)",
                },
            },
            settings={
                "spoken_alerts_enabled": True,
                "privacy_mode": False,
                "autonomy_mode": "semi",
                "operator_persona_enabled": True,
            },
        )
        spoken = payload["spoken_alert"]
        self.assertTrue(spoken["eligible"])
        self.assertEqual("autonomy_advisory", spoken["reason"])
        self.assertIn("DashPro", spoken["message"])
        self.assertIn("Fleet quiet", spoken["message"])

    def test_semi_autonomy_skips_readiness_only_advisory(self) -> None:
        payload = build_operator_presence(
            {
                "top_signals": [],
                "pending_approvals": {"count": 0},
                "degraded": {"active": False},
                "connectivity": {"watch_connected": True},
                "production_readiness": {
                    "score": 100,
                    "grade": "ready",
                    "summary": "Production is 100%",
                },
            },
            settings={
                "spoken_alerts_enabled": True,
                "privacy_mode": False,
                "autonomy_mode": "semi",
                "operator_persona_enabled": True,
            },
        )
        spoken = payload["spoken_alert"]
        self.assertFalse(spoken["eligible"])

    def test_manual_autonomy_stays_silent_without_interruptive_signal(self) -> None:
        payload = build_operator_presence(
            {
                "top_signals": [],
                "pending_approvals": {"count": 0},
                "degraded": {"active": False},
                "connectivity": {"watch_connected": True},
                "advise": "Should not speak in manual mode.",
            },
            settings={
                "spoken_alerts_enabled": True,
                "privacy_mode": False,
                "autonomy_mode": "manual",
            },
        )
        spoken = payload["spoken_alert"]
        self.assertFalse(spoken["eligible"])
        self.assertEqual("no_interruptive_signal", spoken["reason"])

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


class OperatorPresenceSettingsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_settings_round_trip_and_briefing_reflects_persisted_persona_toggle(self) -> None:
        with patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-05T10:00:00Z"),
        ), patch(
            "app.runtime_summary_assembler.runtime_status_snapshot",
            return_value={"families": {}, "records": []},
        ):
            enabled_briefing = self.client.get("/api/briefing").json()
        self.assertTrue(
            enabled_briefing["operator_presence"]["settings"]["operator_persona_enabled"]
        )
        self.assertTrue(
            enabled_briefing["operator_presence"]["persona_voice_line"].startswith("VAXON:")
        )

        save = self.client.put(
            "/api/operator-presence/settings",
            json={"operator_persona_enabled": False},
        )
        self.assertEqual(200, save.status_code)
        self.assertFalse(save.json()["settings"]["operator_persona_enabled"])

        loaded = self.client.get("/api/operator-presence/settings").json()
        self.assertFalse(loaded["settings"]["operator_persona_enabled"])

        with patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-05T10:00:00Z"),
        ), patch(
            "app.runtime_summary_assembler.runtime_status_snapshot",
            return_value={"families": {}, "records": []},
        ):
            disabled_briefing = self.client.get("/api/briefing").json()

        voice_line = disabled_briefing["operator_presence"]["persona_voice_line"]
        self.assertNotIn("KAIRO", voice_line)
        self.assertEqual(
            enabled_briefing["pending_approvals"]["count"],
            disabled_briefing["pending_approvals"]["count"],
        )
        self.assertEqual(
            enabled_briefing["notice"],
            disabled_briefing["notice"],
        )

    def test_ide_voice_strip_setting_round_trip(self) -> None:
        save = self.client.put(
            "/api/operator-presence/settings",
            json={"ide_voice_strip_enabled": True},
        )
        self.assertEqual(200, save.status_code)
        self.assertTrue(save.json()["settings"]["ide_voice_strip_enabled"])

        loaded = self.client.get("/api/operator-presence/settings").json()
        self.assertTrue(loaded["settings"]["ide_voice_strip_enabled"])

    def test_vaxon_model_id_defaults_and_round_trip(self) -> None:
        loaded = self.client.get("/api/operator-presence/settings").json()
        self.assertEqual("cursor-grok-4.5-high-fast", loaded["settings"]["vaxon_model_id"])

        save = self.client.put(
            "/api/operator-presence/settings",
            json={"vaxon_model_id": "composer-2"},
        )
        self.assertEqual(200, save.status_code)
        self.assertEqual("composer-2", save.json()["settings"]["vaxon_model_id"])

        reloaded = self.client.get("/api/operator-presence/settings").json()
        self.assertEqual("composer-2", reloaded["settings"]["vaxon_model_id"])


if __name__ == "__main__":
    unittest.main()
