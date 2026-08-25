"""Per-runtime hook documents that route every agent Bash call through one policy.

Split out of ``agent_sandbox.py`` per its ratchet target. Cursor reads
``.cursor/hooks.json``; Claude Code reads ``.claude/settings.json``. Both point
at the same hook script and the same policy.json, so the allowlist is enforced
identically on every runtime instead of only on Cursor.
"""

from __future__ import annotations

from pathlib import Path

_SANDBOX_POLICY_ROOT = Path("/run/axon-agent-policy")
_HOOK_TIMEOUT_SECONDS = 5


def _hooks_document() -> dict[str, object]:
    hook_command = (
        f"/usr/bin/python3 {_SANDBOX_POLICY_ROOT}/hook.py "
        f"{_SANDBOX_POLICY_ROOT}/policy.json"
    )
    definition = {
        "command": hook_command,
        "failClosed": True,
        "timeout": _HOOK_TIMEOUT_SECONDS,
    }
    return {
        "version": 1,
        "hooks": {
            "beforeShellExecution": [definition],
            "preToolUse": [{**definition, "matcher": "Shell"}],
        },
    }


def _claude_settings_document() -> dict[str, object]:
    """Claude Code settings that route Bash through the same Axon policy hook.

    Cursor reads .cursor/hooks.json; Claude Code reads .claude/settings.json.
    Without this, Axon's approved_command_prefixes were enforced only on the
    Cursor runtime, and the Claude runtime fell back to interactive approval as
    its sole command gate.
    """
    hook_command = (
        f"/usr/bin/python3 {_SANDBOX_POLICY_ROOT}/hook.py "
        f"{_SANDBOX_POLICY_ROOT}/policy.json"
    )
    return {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": hook_command,
                            "timeout": _HOOK_TIMEOUT_SECONDS,
                        }
                    ],
                }
            ]
        }
    }

__all__ = ["_claude_settings_document", "_hooks_document"]
