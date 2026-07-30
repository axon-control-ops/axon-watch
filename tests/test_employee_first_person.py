"""First-person rewrite for employee third-person self-narration."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.employee_first_person import (  # noqa: E402
    employee_name_from_persona_block,
    rewrite_employee_third_person_to_first,
)
from app.workspace_agents.employee_persona_prompt import EMPLOYEE_PERSONA_MARKER  # noqa: E402


class EmployeeFirstPersonTests(unittest.TestCase):
    def test_rewrites_lindi_third_person_progress(self) -> None:
        raw = (
            "Lindi is planning activities and assignments for grades 1–4 to help "
            "students pass term 3. I will check the roster and run the Critical Review "
            "before making changes."
        )
        rewritten = rewrite_employee_third_person_to_first(raw, "Lindi")
        self.assertTrue(rewritten.startswith("I am planning activities"))
        self.assertNotIn("Lindi is", rewritten)
        self.assertIn("I will check the roster", rewritten)

    def test_rewrites_possessive_and_as_name(self) -> None:
        rewritten = rewrite_employee_third_person_to_first(
            "As Lindi, pulling Lindi's receipts now.",
            "Lindi",
        )
        self.assertNotIn("Lindi", rewritten)
        self.assertIn("my receipts", rewritten)

    def test_name_from_persona_block(self) -> None:
        block = (
            f"{EMPLOYEE_PERSONA_MARKER}\n"
            "You are Lindi. Your role is lead for workspace workspace_edudashpro_school.\n"
        )
        self.assertEqual("Lindi", employee_name_from_persona_block(block))


if __name__ == "__main__":
    unittest.main()
