"""Unit tests for VAXON voice autonomy tiers."""

from __future__ import annotations

import unittest

from app.kairo.voice_autonomy import resolve_voice_action_tier
from app.kairo.voice_dispatch import route_voice_turn


class VoiceAutonomyTests(unittest.TestCase):
    def test_reversible_auto_intents(self) -> None:
        for content in ("git status", "health", "ls", "read README.md"):
            decision = resolve_voice_action_tier(content)
            self.assertEqual(decision.tier, "reversible_auto")
            self.assertTrue(decision.auto_execute)
            self.assertFalse(decision.requires_approval)

    def test_shell_and_resume_require_approval(self) -> None:
        for content in ("run npm run verify", "resume from review"):
            decision = resolve_voice_action_tier(content)
            self.assertEqual(decision.tier, "approval_gated")
            self.assertTrue(decision.requires_approval)
            self.assertFalse(decision.auto_execute)

    def test_check_health_shortcut_is_reversible_auto(self) -> None:
        for content in (
            "check health",
            "check-health",
            "run ./scripts/dev/check-health.sh",
        ):
            decision = resolve_voice_action_tier(content)
            self.assertEqual(decision.tier, "reversible_auto", content)
            self.assertTrue(decision.auto_execute, content)
            self.assertFalse(decision.requires_approval, content)

    def test_unsupported_is_gated(self) -> None:
        decision = resolve_voice_action_tier("did you commit?")
        self.assertEqual(decision.tier, "unsupported")
        self.assertTrue(decision.requires_approval)

    def test_router_enforces_tier_and_updates_pending_confirmation(self) -> None:
        remembered: dict[str, object] = {}

        def route(content: str):
            return route_voice_turn(
                content=content,
                session_id="tier-defense",
                workspace_id="workspace_alpha",
                pack={},
                turn_kind="command",
                voice_routing_mode="template_first",
                use_runtime=False,
                answer_tier="fast",
                recent_turns=[],
                command_ack_line=lambda command, **_kwargs: f"Run {command}",
                workspace_short_label=lambda _pack: "Alpha",
                build_runtime_artifact=lambda **_kwargs: {},
                build_runtime_context_block=lambda **_kwargs: "",
                remember_entities=lambda _session_id, **values: remembered.update(values),
                remember_top_signal=lambda *_args, **_kwargs: None,
                dispatch_runtime=lambda **_kwargs: {},
            )

        gated = route("run npm run verify")
        self.assertEqual("approval_gated", gated.action_tier)
        self.assertTrue(gated.requires_confirmation)
        self.assertEqual("run npm run verify", remembered["pending_command"])

        automatic = route("health")
        self.assertEqual("reversible_auto", automatic.action_tier)
        self.assertFalse(automatic.requires_confirmation)
        self.assertEqual("", remembered["pending_command"])


if __name__ == "__main__":
    unittest.main()
