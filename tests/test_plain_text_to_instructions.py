from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.plain_text_to_instructions import (  # noqa: E402
    instructions_block_git_actions,
    prompt_requests_git_actions,
)


class PlainTextToInstructionsTests(unittest.TestCase):
    def test_negated_commit_mention_is_not_git_intent(self) -> None:
        prompt = (
            "Look at what Dashpro workspace said about the CI work and plan how the "
            "Agents we have built would handle that. I never said anything about committing."
        )
        self.assertFalse(prompt_requests_git_actions(prompt))

    def test_instructions_out_of_scope_blocks_git(self) -> None:
        prompt = """# Instructions

## Goal
Plan CI handling.

## Out of scope
- Committing, amending, or inventing commit chores

## Steps
1. Read the triage note.
"""
        self.assertTrue(instructions_block_git_actions(prompt))
        self.assertFalse(prompt_requests_git_actions(prompt))

    def test_explicit_commit_still_detected(self) -> None:
        self.assertTrue(prompt_requests_git_actions("commit these changes"))
        self.assertTrue(prompt_requests_git_actions("please commit and push"))


if __name__ == "__main__":
    unittest.main()
