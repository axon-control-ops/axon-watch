from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.plain_text_to_instructions import (  # noqa: E402
    build_instructions_markdown_from_source,
    compose_instructions_markdown,
    extract_instructions_markdown,
    instructions_block_git_actions,
    instructions_markdown_is_complete,
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

    def test_extract_instructions_from_fenced_markdown(self) -> None:
        raw = """Here is the brief:

```markdown
# Instructions

## Goal
Fix GIF rendering.

## Source request
Make GIFs look like WhatsApp.
```"""
        extracted = extract_instructions_markdown(raw)
        self.assertIsNotNone(extracted)
        self.assertTrue(extracted.startswith("# Instructions"))
        self.assertIn("Fix GIF rendering.", extracted or "")

    def test_extract_instructions_after_preamble(self) -> None:
        raw = "Sure — converted below.\n\n# Instructions\n\n## Goal\nShip OTA safely.\n\n## In scope\n- OTA\n\n## Out of scope\n- Commit\n\n## Steps\n1. One\n2. Two\n3. Three\n\n## Constraints\n- Safe\n\n## Source request\nShip OTA safely.\n"
        extracted = extract_instructions_markdown(raw)
        self.assertTrue(extracted is not None and extracted.startswith("# Instructions"))

    def test_build_instructions_from_long_source(self) -> None:
        source = (
            "Connect the Young Eagles workspace as Teacher-X in DashPro. "
            "The team needs to know layout, features, screens, homework, assignments, grading, "
            "reports, and official languages for preschool and K-12."
        )
        built = build_instructions_markdown_from_source(source)
        self.assertTrue(instructions_markdown_is_complete(built))
        self.assertIn("Teacher-X", built)
        self.assertIn("## Source request", built)

    def test_compose_instructions_fills_missing_model_sections(self) -> None:
        source = "Fix GIF rendering on mobile before OTA."
        model = "# Instructions\n\n## Source request\nFix GIF rendering on mobile before OTA.\n"
        composed = compose_instructions_markdown(source, model)
        self.assertTrue(instructions_markdown_is_complete(composed))
        self.assertIn("## Steps", composed)

    def test_commit_sha_reference_is_not_git_intent(self) -> None:
        self.assertFalse(
            prompt_requests_git_actions(
                "Real DashPro fix commit: 2c0870708ddaa54550fb602c7fd3026c46e7ebb3"
            )
        )
        self.assertFalse(
            prompt_requests_git_actions(
                "Publish the verified commit 2c0870708ddaa54550fb602c7fd3026c46e7ebb3 to canary"
            )
        )


if __name__ == "__main__":
    unittest.main()
