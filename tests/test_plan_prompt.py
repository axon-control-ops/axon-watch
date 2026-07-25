from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.router import _system_prompt  # noqa: E402
from app.chat.lane_b_system_content import lane_b_system_content  # noqa: E402


class PlanPromptTests(unittest.TestCase):
    def test_plan_prompt_requires_durable_markdown_plan_contract(self) -> None:
        prompt = _system_prompt(
            "plan",
            research_snapshot={"available": False},
        )

        self.assertIn("Produce a complete durable plan", prompt)
        self.assertIn(":::ask", prompt)
        self.assertIn("## Sources", prompt)
        self.assertIn("## Verification checklist", prompt)
        self.assertIn("Do not claim execution happened", prompt)
        self.assertIn("offline limits", prompt.lower())

    def test_plan_system_message_exposes_linked_run_state(self) -> None:
        content = lane_b_system_content(
            composer_mode="plan",
            dispatch_run_id="run_plan",
            dispatched=True,
            run_phase="review_ready",
        )
        self.assertIn("run_plan", content)
        self.assertIn("review_ready", content)


if __name__ == "__main__":
    unittest.main()
