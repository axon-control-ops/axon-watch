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


if __name__ == "__main__":
    unittest.main()
