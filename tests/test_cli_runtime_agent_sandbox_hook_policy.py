"""Shell-hook command policy cases (split from the sandbox contract suite)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.agent_shell_hook import evaluate_hook_payload  # noqa: E402


class AgentShellHookCommandPolicyTests(unittest.TestCase):
    def test_explicit_read_only_prefix_survives_the_network_tool_deny(self) -> None:
        """Regression: `gh` is a raw network tool, so an operator-approved
        read-only sub-command was denied before the prefix was ever consulted,
        making the configured gh read prefixes dead config."""
        response = evaluate_hook_payload(
            {"hook_event_name": "beforeShellExecution", "command": "gh auth status"},
            approved_wrappers=frozenset(),
            approved_command_prefixes=(("gh", "auth", "status"), ("gh", "run", "list")),
        )
        self.assertEqual("allow", response["permission"])

    def test_network_tool_stays_denied_outside_its_approved_sub_commands(self) -> None:
        prefixes = (("gh", "auth", "status"), ("gh", "run", "list"))
        for command in (
            "gh pr merge 12",
            "gh repo delete acme/app",
            "gh auth login",
            "gh run rerun 7",
            "curl https://example.invalid",
        ):
            with self.subTest(command=command):
                response = evaluate_hook_payload(
                    {"hook_event_name": "beforeShellExecution", "command": command},
                    approved_wrappers=frozenset(),
                    approved_command_prefixes=prefixes,
                )
                self.assertEqual("deny", response["permission"])

    def test_bare_single_token_network_prefix_cannot_open_the_tool(self) -> None:
        """A sloppy ("gh",) entry must not approve every gh sub-command."""
        response = evaluate_hook_payload(
            {"hook_event_name": "beforeShellExecution", "command": "gh repo delete acme/app"},
            approved_wrappers=frozenset(),
            approved_command_prefixes=(("gh",),),
        )
        self.assertEqual("deny", response["permission"])

    def test_python3_repo_scripts_allowed_with_scripts_prefix(self) -> None:
        response = evaluate_hook_payload(
            {
                "hook_event_name": "beforeShellExecution",
                "command": "python3 scripts/fill-rfq26052-pdf.py",
            },
            approved_wrappers=frozenset(),
            approved_command_prefixes=(("python3", "scripts/"), ("pdftotext",)),
        )
        self.assertEqual("allow", response["permission"])

    def test_python3_outside_scripts_stays_denied(self) -> None:
        response = evaluate_hook_payload(
            {"hook_event_name": "beforeShellExecution", "command": "python3 -c print(1)"},
            approved_wrappers=frozenset(),
            approved_command_prefixes=(("python3", "scripts/"),),
        )
        self.assertEqual("deny", response["permission"])


if __name__ == "__main__":
    unittest.main()


class QuotedMetacharacterTests(unittest.TestCase):
    """Quoted metacharacters are data, not shell syntax."""

    def _decide(self, command: str) -> str:
        return evaluate_hook_payload(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": command},
            },
            approved_wrappers=frozenset({"axon-agent-terminal-job"}),
            approved_command_prefixes=(("git", "grep"), ("grep",), ("rg",)),
        )["permission"]

    def test_regex_alternation_in_quotes_is_allowed(self) -> None:
        # This exact shape was denied and cost agents repeated turns.
        self.assertEqual(
            self._decide('git grep -n "insert\\|from(" components/x.tsx'), "allow"
        )
        self.assertEqual(self._decide("grep -n 'a|b' file.ts"), "allow")

    def test_real_shell_operators_are_still_denied(self) -> None:
        for command in (
            "grep -n a file | wc -l",
            "grep -n a file; rm -rf x",
            "grep -n a file && rm x",
            "grep -n a file > out.txt",
        ):
            with self.subTest(command=command):
                self.assertEqual(self._decide(command), "deny")

    def test_expansion_inside_double_quotes_is_still_denied(self) -> None:
        # Double quotes do not stop $() or backticks, so these stay dangerous.
        for command in ('grep -n "$(id)" file', 'grep -n "`id`" file'):
            with self.subTest(command=command):
                self.assertEqual(self._decide(command), "deny")

    def test_unbalanced_quoting_fails_closed(self) -> None:
        self.assertEqual(self._decide("grep -n 'unterminated file"), "deny")

    def test_backslash_escape_outside_quotes_is_denied(self) -> None:
        self.assertEqual(self._decide("grep -n a file \\| wc -l"), "deny")
