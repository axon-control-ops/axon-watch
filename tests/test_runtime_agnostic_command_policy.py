"""One command policy, enforced identically on every agent runtime.

Axon's approved_command_prefixes used to be wired only into Cursor's
.cursor/hooks.json. The Claude runtime never read them, so its interactive
approval prompt was the only command gate — which is why a Full Access shift
could edit files but never run a test.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.agent_sandbox_hook_docs import (  # noqa: E402
    _claude_settings_document,
    _hooks_document,
)
from app.cli_runtime.agent_shell_hook import (  # noqa: E402
    evaluate_hook_payload,
    to_claude_hook_response,
)

PREFIXES = (("npm", "ci"), ("npm", "test"), ("npx", "--no-install", "jest"), ("gh", "run", "list"))


def _decide(command: str, *, tool_name: str, event_name: str = "preToolUse") -> dict:
    return evaluate_hook_payload(
        {
            "hook_event_name": event_name,
            "tool_name": tool_name,
            "tool_input": {"command": command},
        },
        approved_wrappers=frozenset({"axon-agent-terminal-job"}),
        approved_command_prefixes=PREFIXES,
    )


class RuntimeParityTests(unittest.TestCase):
    def test_claude_canonical_pre_tool_use_event_is_accepted(self) -> None:
        decision = _decide(
            "npm test -- tests/x.test.tsx",
            tool_name="Bash",
            event_name="PreToolUse",
        )
        self.assertEqual("allow", decision["permission"])

    def test_claude_bash_tool_reaches_the_same_policy_as_cursor_shell(self) -> None:
        for command, expected in (
            ("npm ci", "allow"),
            ("npm test -- tests/x.test.tsx", "allow"),
            ("npx --no-install jest tests/x.test.tsx", "allow"),
            ("npx jest tests/x.test.tsx", "deny"),
            ("axon-agent-terminal-job --workspace w -- npx jest tests/x", "allow"),
            ("curl https://example.invalid", "deny"),
            ("sudo rm -rf /", "deny"),
            ("node -e \"1\"", "deny"),
            ("gh pr merge 12", "deny"),
        ):
            with self.subTest(command=command):
                cursor = _decide(command, tool_name="Shell")["permission"]
                claude = _decide(command, tool_name="Bash")["permission"]
                self.assertEqual(expected, cursor)
                self.assertEqual(cursor, claude, "runtimes must agree")

    def test_decision_is_expressed_in_claude_schema(self) -> None:
        allowed = to_claude_hook_response(_decide("npm test", tool_name="Bash"))
        denied = to_claude_hook_response(_decide("curl https://x.invalid", tool_name="Bash"))

        self.assertEqual(
            "allow", allowed["hookSpecificOutput"]["permissionDecision"]
        )
        self.assertEqual("deny", denied["hookSpecificOutput"]["permissionDecision"])
        self.assertEqual("PreToolUse", denied["hookSpecificOutput"]["hookEventName"])
        self.assertTrue(denied["hookSpecificOutput"]["permissionDecisionReason"])
        # Cursor's key must survive alongside Claude's.
        self.assertEqual("deny", denied["permission"])

    def test_an_unknown_tool_still_fails_closed(self) -> None:
        self.assertEqual("deny", _decide("npm test", tool_name="WebFetch")["permission"])


class HookDocumentTests(unittest.TestCase):
    def test_both_runtimes_point_at_the_same_hook_and_policy(self) -> None:
        cursor = json.loads(json.dumps(_hooks_document()))
        claude = json.loads(json.dumps(_claude_settings_document()))

        cursor_cmd = cursor["hooks"]["beforeShellExecution"][0]["command"]
        claude_cmd = claude["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        self.assertEqual(cursor_cmd, claude_cmd)
        self.assertIn("policy.json", claude_cmd)
        self.assertEqual("Bash", claude["hooks"]["PreToolUse"][0]["matcher"])


if __name__ == "__main__":
    unittest.main()
