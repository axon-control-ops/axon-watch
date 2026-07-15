"""Unit tests for VAXON voice autonomy tiers."""

from __future__ import annotations

import unittest

from app.kairo.voice_autonomy import resolve_voice_action_tier


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


if __name__ == "__main__":
    unittest.main()
