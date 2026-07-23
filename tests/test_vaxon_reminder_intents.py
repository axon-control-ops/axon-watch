"""Conversational reminder intents + opportunistic speech policy tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.host_context import reminders as reminder_engine  # noqa: E402
from app.kairo.opportunistic_speech import SpeechBudget, choose_opportunistic_speech  # noqa: E402
from app.kairo.reminder_intents import (  # noqa: E402
    clear_pending_for_tests,
    maybe_handle_reminder_intent,
    parse_reminder_request,
)
from app.persistence import operator_memory_store, run_store  # noqa: E402


class ReminderIntentTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        clear_pending_for_tests()

    def test_parse_remind_me_in_minutes(self) -> None:
        parsed = parse_reminder_request(
            "remind me to stretch in 20 minutes",
            timezone_name="UTC",
        )
        assert parsed is not None
        self.assertIn("stretch", str(parsed["title"]).lower())
        self.assertTrue(parsed["needs_confirmation"])

    def test_confirm_persists_via_existing_reminder_engine(self) -> None:
        first = maybe_handle_reminder_intent(
            content="remind me to call Sam in 30 minutes",
            session_id="sess_1",
            workspace_id="workspace_axon_watch",
        )
        assert first is not None
        self.assertEqual("reminder_confirm_required", first["action"]["type"])
        second = maybe_handle_reminder_intent(
            content="confirm",
            session_id="sess_1",
            workspace_id="workspace_axon_watch",
        )
        assert second is not None
        self.assertEqual("reminder_created", second["action"]["type"])
        open_items = reminder_engine.list_open_loops(workspace_id="workspace_axon_watch", limit=5)
        self.assertTrue(any("call Sam" in str(item.get("title") or "") for item in open_items))


class OpportunisticSpeechTests(unittest.TestCase):
    def test_policy_requires_active_console_and_budget(self) -> None:
        budget = SpeechBudget(max_interruptions_per_hour=1)
        choice = choose_opportunistic_speech(
            due_reminders=[{"title": "Stretch", "memory_id": "m1"}],
            open_loops=[],
            material_incidents=[],
            budget=budget,
            console_active=False,
            quiet_hours=False,
        )
        self.assertIsNone(choice)
        choice = choose_opportunistic_speech(
            due_reminders=[{"title": "Stretch", "memory_id": "m1"}],
            open_loops=[],
            material_incidents=[],
            budget=budget,
            console_active=True,
            quiet_hours=False,
        )
        self.assertEqual("reminder", choice and choice["kind"])
        blocked = choose_opportunistic_speech(
            due_reminders=[{"title": "Another", "memory_id": "m2"}],
            open_loops=[],
            material_incidents=[],
            budget=budget,
            console_active=True,
            quiet_hours=False,
        )
        self.assertIsNone(blocked)


if __name__ == "__main__":
    unittest.main()
