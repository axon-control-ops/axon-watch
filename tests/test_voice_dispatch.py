"""Unit tests for VAXON voice dispatch routing helpers."""

from __future__ import annotations

import unittest

from app.kairo.voice_dispatch import (
    normalize_voice_routing_mode,
    should_use_vaxon_runtime,
    vaxon_model_pool,
)


class VoiceDispatchTests(unittest.TestCase):
    def test_normalize_routing_mode(self) -> None:
        self.assertEqual(normalize_voice_routing_mode("runtime_aggressive"), "runtime_aggressive")
        self.assertEqual(normalize_voice_routing_mode("nope"), "template_first")

    def test_template_first_never_uses_runtime(self) -> None:
        self.assertFalse(
            should_use_vaxon_runtime(
                turn_kind="open_question",
                content="why is dashpro degraded?",
                use_runtime=False,
                answer_tier="deep",
                voice_routing_mode="template_first",
            )
        )
        self.assertTrue(
            should_use_vaxon_runtime(
                turn_kind="open_question",
                content="why is dashpro degraded?",
                use_runtime=True,
                answer_tier="deep",
                voice_routing_mode="template_first",
            )
        )

    def test_runtime_on_deep_requires_deep_or_detail(self) -> None:
        self.assertTrue(
            should_use_vaxon_runtime(
                turn_kind="open_question",
                content="explain the outage",
                use_runtime=False,
                answer_tier="deep",
                voice_routing_mode="runtime_on_deep",
            )
        )
        self.assertFalse(
            should_use_vaxon_runtime(
                turn_kind="open_question",
                content="hi",
                use_runtime=False,
                answer_tier="fast",
                voice_routing_mode="runtime_on_deep",
            )
        )

    def test_model_pool_non_empty(self) -> None:
        self.assertGreaterEqual(len(vaxon_model_pool()), 1)


if __name__ == "__main__":
    unittest.main()
