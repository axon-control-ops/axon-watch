from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.command_executor import classify_command, execute_command  # noqa: E402
from app.chat.command_intent import (  # noqa: E402
    command_requires_confirmation,
    expand_command_shortcuts,
)
from app.chat.dispatch import build_command_dispatch_ack  # noqa: E402
from app.chat.command_executor import CommandExecutionResult  # noqa: E402


class CommandShortcutTests(unittest.TestCase):
    def test_expand_check_health_shortcut(self) -> None:
        self.assertEqual(
            expand_command_shortcuts("check-health"),
            "run ./scripts/dev/check-health.sh",
        )

    def test_expand_verify_shortcut(self) -> None:
        self.assertEqual(
            expand_command_shortcuts("verify"),
            "run npm run verify:production-operator",
        )

    def test_expand_dashpro_ota_shortcut(self) -> None:
        self.assertEqual(
            expand_command_shortcuts("ota canary"),
            "run npm run ota:canary",
        )

    def test_classify_shortcuts_as_shell_command(self) -> None:
        self.assertEqual(classify_command("check-health"), "shell_command")
        self.assertEqual(classify_command("verify"), "shell_command")
        self.assertEqual(classify_command("ota canary"), "shell_command")

    def test_check_health_does_not_require_confirmation(self) -> None:
        self.assertFalse(command_requires_confirmation("check health"))
        self.assertFalse(command_requires_confirmation("check-health"))
        self.assertTrue(command_requires_confirmation("verify"))

    def test_questions_are_not_commands(self) -> None:
        for prompt in (
            "Did you commit and push",
            "what does the readme say?",
            "is the health check passing?",
            "how do I run git status?",
        ):
            self.assertEqual(classify_command(prompt), "unsupported", prompt)

    def test_imperative_commands_still_classify(self) -> None:
        self.assertEqual(classify_command("read README.md"), "read_file")
        self.assertEqual(classify_command("show the readme"), "read_file")
        self.assertEqual(classify_command("git status"), "git_status")

    def test_question_style_git_status_normalizes_to_command(self) -> None:
        self.assertEqual(expand_command_shortcuts("what is the git status?"), "git status")
        self.assertEqual(classify_command(expand_command_shortcuts("what is the git status?")), "git_status")
        self.assertEqual(expand_command_shortcuts("can you run git status?"), "git status")

    def test_dispatch_ack_includes_execution_summary(self) -> None:
        execution = CommandExecutionResult(
            intent="shell_command",
            success=True,
            output="ok",
            receipt_summary="Shell command succeeded",
        )
        ack = build_command_dispatch_ack(
            run_id="run_demo",
            phase="review_ready",
            dispatched=True,
            execution=execution,
        )
        self.assertIn("executed shell_command (ok)", ack)


if __name__ == "__main__":
    unittest.main()
