"""Unit tests for cited mission memory and advise→confirm flows."""

from __future__ import annotations

import unittest

from app.kairo.mission_memory import (
    active_mission,
    clear_mission,
    is_polite_work_request,
    maybe_capture_explicit_remember,
    override_mission_with_live_dto,
    propose_mission_action,
    resolve_mission_confirmation,
)
from app.kairo.turn_memory import clear_memory_for_tests


class MissionMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_memory_for_tests()

    def test_explicit_remember_only(self) -> None:
        self.assertIsNone(maybe_capture_explicit_remember("s1", "the weather is fine"))
        captured = maybe_capture_explicit_remember("s1", "Remember: ship continuous VAXON parity")
        self.assertIsNotNone(captured)
        mission = active_mission("s1")
        assert mission is not None
        self.assertIn("continuous VAXON", mission["mission"])

    def test_live_dto_overrides_memory(self) -> None:
        maybe_capture_explicit_remember("s1", "Remember: old mission")
        override_mission_with_live_dto("s1", live_mission="live mission wins", live_workspace_id="ws-1")
        mission = active_mission("s1")
        assert mission is not None
        self.assertEqual(mission["mission"], "live mission wins")
        self.assertEqual(mission["workspace_id"], "ws-1")

    def test_work_request_is_advise_only_until_confirm(self) -> None:
        self.assertTrue(is_polite_work_request("Can you start working on the orb?"))
        self.assertFalse(is_polite_work_request("Why is the orb slow?"))
        proposal = propose_mission_action("s1", "Start working on the orb", workspace_id="ws-a")
        assert proposal is not None
        self.assertEqual(proposal["kind"], "advise_confirm")
        self.assertIsNone(proposal["action"])
        self.assertTrue(proposal["requires_confirmation"])

        rejected = resolve_mission_confirmation("s1", "cancel")
        assert rejected is not None
        self.assertEqual(rejected["kind"], "rejected")

        propose_mission_action("s1", "Start working on the orb", workspace_id="ws-a")
        confirmed = resolve_mission_confirmation("s1", "confirm")
        assert confirmed is not None
        self.assertEqual(confirmed["kind"], "confirmed_handoff")
        self.assertEqual(confirmed["action"]["type"], "dispatch_command")
        self.assertIn("handoff", confirmed["action"]["content"])

    def test_pending_confirmation_expires(self) -> None:
        propose_mission_action(
            "s1",
            "Start working on the orb",
            workspace_id="ws-a",
            confirm_ttl_seconds=1,
        )
        # Force expiry by rewriting the pending deadline into the past.
        from app.kairo.turn_memory import remember_entities

        remember_entities("s1", pending_mission_expires_at="1")
        expired = resolve_mission_confirmation("s1", "maybe later")
        assert expired is not None
        self.assertEqual(expired["kind"], "expired")

    def test_clear_mission(self) -> None:
        maybe_capture_explicit_remember("s1", "Remember: temporary")
        clear_mission("s1")
        self.assertIsNone(active_mission("s1"))


if __name__ == "__main__":
    unittest.main()
