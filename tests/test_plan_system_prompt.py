"""Unit tests for Plan-mode system prompt sources + ask fence instructions."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.plan_system_prompt import (  # noqa: E402
    ask_fence_instruction,
    build_plan_system_prompt,
)


class PlanSystemPromptTests(unittest.TestCase):
    def test_requires_sources_and_ask_fence(self) -> None:
        prompt = build_plan_system_prompt(
            offline_clause="Ground locally. ",
            research_line="research:ok",
            instruction_taking="follow instructions",
            reply_style="be concise",
        )
        self.assertIn("## Sources", prompt)
        self.assertIn("axon_research_search", prompt)
        self.assertIn(":::ask", prompt)
        self.assertIn("Do NOT call CreatePlan", prompt)
        self.assertNotIn("Reply with 1, 2, or 3", prompt.split("QUESTIONS:")[0])

    def test_ask_fence_instruction_for_agent_modes(self) -> None:
        line = ask_fence_instruction()
        self.assertIn(":::ask", line)
        self.assertIn("AskQuestion", line)
        self.assertIn("Selected option", line)
        self.assertIn("do not re-ask what the options were", line)

    def test_ask_fence_instruction_also_forbids_create_plan(self) -> None:
        """Regression: Agent-mode prompts only warned against AskQuestion, not
        CreatePlan — a watcher run called CreatePlan anyway and it hung, leaving
        an empty tool block (":::") instead of the agent's actual findings."""
        line = ask_fence_instruction()
        self.assertIn("CreatePlan", line)
        self.assertIn("hang", line)


if __name__ == "__main__":
    unittest.main()
