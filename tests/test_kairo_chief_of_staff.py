from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo.voice_dispatch import should_use_vaxon_runtime  # noqa: E402
from app.kairo_ask_prompt import build_ask_system_prompt  # noqa: E402
from app.kairo_chief_of_staff import (  # noqa: E402
    CHIEF_OF_STAFF_MARKER,
    build_chief_of_staff_context_block,
    charter_path,
    clear_chief_of_staff_charter_cache,
    load_vaxon_chief_of_staff_charter,
)
from app.kairo_conversation_runtime_context import build_runtime_context_block  # noqa: E402


class KairoChiefOfStaffTests(unittest.TestCase):
    def tearDown(self) -> None:
        clear_chief_of_staff_charter_cache()

    def test_charter_file_exists_and_loads(self) -> None:
        path = charter_path()
        self.assertTrue(path.is_file(), f"missing charter at {path}")
        text = load_vaxon_chief_of_staff_charter()
        self.assertIn("You are VAXON", text)
        self.assertIn("Chief of Staff", text)
        self.assertIn("deterministic", text.lower())

    def test_ask_prompt_embeds_full_charter(self) -> None:
        prompt = build_ask_system_prompt(persona_enabled=True)
        self.assertIn(CHIEF_OF_STAFF_MARKER, prompt)
        self.assertIn("Mission Lifecycle", prompt)
        self.assertIn("not a coding assistant", prompt.lower())
        self.assertIn("read-only", prompt)

    def test_runtime_context_uses_compact_charter(self) -> None:
        with patch(
            "app.kairo_conversation_runtime_context.build_lane_b_context_block",
            return_value="LANE_B_CTX",
        ), patch(
            "app.kairo_conversation_runtime_context.build_conversation_facts",
            return_value={
                "pending_approvals": 0,
                "top_signal_title": "",
                "top_signal_summary": "",
                "active_run_count": 0,
                "primary_run_summary": "",
                "degraded": False,
                "cli_dispatch_ready": True,
                "cli_blockers": [],
                "notice": "",
                "advise": "",
            },
        ):
            block = build_runtime_context_block(
                content="hello",
                workspace_id="workspace_axon_watch",
                pack={},
                session_id="sess_test",
                recent_turns=[],
            )
        self.assertIn(CHIEF_OF_STAFF_MARKER, block)
        self.assertIn("deterministic lane", block.lower())
        # Compact: identity present; full lifecycle section should not be required twice.
        compact = build_chief_of_staff_context_block(include_full_charter=False)
        self.assertLess(len(compact), len(build_chief_of_staff_context_block(include_full_charter=True)))

    def test_long_open_question_forces_runtime_even_on_fast_tier(self) -> None:
        long_prompt = "You are VAXON.\n" + ("plan the mission. " * 40)
        self.assertTrue(
            should_use_vaxon_runtime(
                turn_kind="open_question",
                content=long_prompt,
                use_runtime=False,
                answer_tier="fast",
                voice_routing_mode="runtime_on_deep",
            )
        )

    def test_short_open_question_still_skips_runtime_on_fast(self) -> None:
        self.assertFalse(
            should_use_vaxon_runtime(
                turn_kind="open_question",
                content="why is sentry spiking?",
                use_runtime=True,
                answer_tier="fast",
                voice_routing_mode="runtime_on_deep",
            )
        )


if __name__ == "__main__":
    unittest.main()
