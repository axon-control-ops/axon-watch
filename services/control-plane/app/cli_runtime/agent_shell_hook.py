"""Deterministic, fail-closed shell policy used by per-run agent hooks."""

from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

_MAX_COMMAND_BYTES = 32_768
_SHELL_META = frozenset(";&|<>`$\\\n\r\x00(){}[]*?!~#")
_RAW_NETWORK_TOOLS = frozenset(
    {
        "aria2c",
        "curl",
        "ftp",
        "gh",
        "http",
        "httpie",
        "nc",
        "netcat",
        "nmap",
        "rsync",
        "scp",
        "sftp",
        "socat",
        "ssh",
        "telnet",
        "wget",
    }
)
_PRIVILEGE_TOOLS = frozenset({"doas", "pkexec", "su", "sudo"})
_INTERPRETER_ESCAPES = frozenset(
    {
        "ash",
        "bash",
        "builtin",
        "bun",
        "busybox",
        "command",
        "dash",
        "deno",
        "env",
        "eval",
        "exec",
        "fish",
        "js",
        "lua",
        "node",
        "perl",
        "php",
        "python",
        "python2",
        "python3",
        "ruby",
        "sh",
        "source",
        "zsh",
    }
)
_DESTRUCTIVE_GIT_SUBCOMMANDS = frozenset(
    {
        "branch",
        "checkout",
        "cherry-pick",
        "clean",
        "commit",
        "config",
        "fetch",
        "merge",
        "pull",
        "push",
        "rebase",
        "remote",
        "reset",
        "restore",
        "revert",
        "switch",
        "tag",
    }
)
_GENERIC_ESCAPE_ARGUMENTS = frozenset(
    {
        "-exec",
        "-execdir",
        "--exec",
        "--exec-path",
        "--config-env",
        "--upload-pack",
        "--receive-pack",
    }
)


def _has_unquoted_shell_meta(command: str) -> bool:
    """True when a shell metacharacter is live rather than quoted data.

    Scanning the raw string rejected ``git grep -n "insert\\|from("`` — the
    pipe is inside quotes and is regex data, not a shell operator. Agents hit
    this constantly on ordinary searches and burned whole turns retrying.

    Quoting rules are followed exactly, because they decide what is actually
    dangerous:

    * single quotes make every character literal, so metas inside them are data;
    * double quotes still allow ``$`` and backtick expansion, so those two stay
      rejected inside them while ``|``, ``;``, ``>`` and friends are data;
    * unquoted metas are rejected exactly as before.

    Unbalanced quoting fails closed — the shell would interpret the remainder in
    a way this scanner cannot predict.
    """
    quote: str | None = None
    index = 0
    while index < len(command):
        character = command[index]
        if quote is None and character == "\\":
            # An unquoted backslash escapes the next character; it is also the
            # classic way to smuggle an operator past a naive scan.
            return True
        if quote == '"' and character == "\\":
            index += 2
            continue
        if quote is None and character in {"'", '"'}:
            quote = character
        elif quote is not None and character == quote:
            quote = None
        elif quote == "'":
            pass  # Literal region: nothing here can reach the shell as syntax.
        elif quote == '"':
            if character in {"$", "`"}:
                return True
        elif character in _SHELL_META:
            return True
        index += 1
    return quote is not None


def _deny(reason: str) -> dict[str, str]:
    return {
        "permission": "deny",
        "user_message": f"Agent sandbox blocked this action: {reason}.",
        "agent_message": f"Sandbox policy denied the action ({reason}). Use an approved wrapper.",
    }


def _allow() -> dict[str, str]:
    return {"permission": "allow"}


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("policy list is malformed")
    result = tuple(str(item) for item in value)
    if any(not item or "\x00" in item for item in result):
        raise ValueError("policy contains an empty or invalid value")
    return result


def _load_policy(
    policy_path: Path,
) -> tuple[frozenset[str], tuple[tuple[str, ...], ...], str]:
    with policy_path.open("r", encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, Mapping) or document.get("version") != 1:
        raise ValueError("unsupported policy document")

    wrappers = frozenset(_string_tuple(document.get("approved_wrappers", ())))
    prefixes_raw = document.get("approved_command_prefixes", ())
    if not isinstance(prefixes_raw, Sequence) or isinstance(prefixes_raw, (str, bytes)):
        raise ValueError("approved command prefixes are malformed")
    prefixes = tuple(_string_tuple(prefix) for prefix in prefixes_raw)
    write_scope_hint = str(document.get("write_scope_hint") or "")
    return wrappers, prefixes, write_scope_hint


def _extract_shell_command(payload: Mapping[str, Any]) -> str:
    raw_event = str(payload.get("hook_event_name") or "").strip()
    # Cursor uses lower-camel event names while Claude Code uses PascalCase.
    # Normalize only the known spelling separators/case; unknown events must
    # still fail closed rather than being treated as shell execution.
    event = "".join(character for character in raw_event.casefold() if character.isalnum())
    if event == "beforeshellexecution":
        command = payload.get("command")
    elif event == "pretooluse":
        tool_name = str(
            payload.get("tool_name")
            or payload.get("tool")
            or payload.get("tool_type")
            or ""
        ).lower()
        # Cursor emits shell/terminal; Claude Code emits Bash. Same gate.
        if tool_name and tool_name not in {"shell", "terminal", "bash"}:
            raise ValueError("unsupported PreToolUse tool")
        tool_input = payload.get("tool_input", payload.get("input"))
        command = tool_input.get("command") if isinstance(tool_input, Mapping) else None
    else:
        raise ValueError("unsupported hook event")

    if not isinstance(command, str) or not command.strip():
        raise ValueError("missing shell command")
    if len(command.encode("utf-8")) > _MAX_COMMAND_BYTES:
        raise ValueError("shell command is too long")
    return command.strip()


def _git_is_destructive(tokens: Sequence[str]) -> bool:
    executable = os.path.basename(tokens[0]).lower()
    if executable != "git":
        return False
    lowered = [token.lower() for token in tokens[1:]]
    if any(token in _GENERIC_ESCAPE_ARGUMENTS or token == "-c" for token in lowered):
        return True
    return any(token in _DESTRUCTIVE_GIT_SUBCOMMANDS for token in lowered)


def _matches_prefix(tokens: Sequence[str], prefix: Sequence[str]) -> bool:
    if len(tokens) < len(prefix):
        if _script_prefix_match(tokens, prefix):
            return True
        return False
    if tuple(tokens[: len(prefix)]) == tuple(prefix):
        return True
    return _script_prefix_match(tokens, prefix)


def _script_prefix_match(tokens: Sequence[str], prefix: Sequence[str]) -> bool:
    """Allow python3 scripts/foo.py and .venv/bin/python3 scripts/foo.py."""
    if len(tokens) < 2 or len(prefix) != 2:
        return False
    exe = os.path.basename(tokens[0]).lower()
    prefix_exe = os.path.basename(prefix[0]).lower()
    if exe != prefix_exe or prefix[1] != "scripts/":
        return False
    if prefix[0] == "python3" and tokens[0] != "python3":
        return False
    if prefix[0] == ".venv/bin/python3" and tokens[0] != ".venv/bin/python3":
        return False
    return str(tokens[1]).startswith("scripts/")


def _interpreter_prefix_approved(
    executable: str,
    tokens: Sequence[str],
    approved_command_prefixes: tuple[tuple[str, ...], ...],
) -> bool:
    if executable not in _INTERPRETER_ESCAPES:
        return False
    return any(_matches_prefix(tokens, prefix) for prefix in approved_command_prefixes)


def evaluate_hook_payload(
    payload: Mapping[str, Any],
    *,
    approved_wrappers: frozenset[str],
    approved_command_prefixes: tuple[tuple[str, ...], ...],
    write_scope_hint: str = "",
) -> dict[str, str]:
    """Return a Cursor hook permission response; malformed input always denies."""
    try:
        command = _extract_shell_command(payload)
    except (TypeError, ValueError) as exc:
        return _deny(str(exc))

    if _has_unquoted_shell_meta(command):
        return _deny("shell operators, expansion, redirection, and escapes are not allowed")

    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return _deny("malformed shell quoting")
    if not tokens:
        return _deny("empty shell command")
    if any(
        token.startswith("/")
        or token == ".."
        or token.startswith("../")
        or "/../" in token
        or token.endswith("/..")
        for token in tokens[1:]
    ):
        return _deny("absolute paths and parent traversal are not allowed")

    executable_token = tokens[0]
    executable = os.path.basename(executable_token).lower()
    if executable_token.startswith("-") or "=" in executable_token:
        return _deny("environment assignments and option-shaped executables are not allowed")
    # An explicitly enumerated multi-token prefix is an operator decision about
    # one specific sub-command (e.g. `gh auth status`). Without this, the
    # blanket network deny below fires first and silently voids that config.
    prefix_match = next(
        (prefix for prefix in approved_command_prefixes if _matches_prefix(tokens, prefix)),
        None,
    )
    narrowly_approved = prefix_match is not None and len(prefix_match) >= 2
    if executable in _PRIVILEGE_TOOLS:
        hint = f" {write_scope_hint}" if write_scope_hint else ""
        return _deny(f"privilege escalation is not allowed — never use sudo/su to work around filesystem restrictions.{hint}")
    if executable in _RAW_NETWORK_TOOLS and not narrowly_approved:
        return _deny("raw network tools are not allowed")
    if executable in _INTERPRETER_ESCAPES and not _interpreter_prefix_approved(
        executable, tokens, approved_command_prefixes
    ):
        return _deny("shell and interpreter escapes are not allowed")
    if executable == "npx" and "--no-install" not in tokens[1:]:
        return _deny("npx must include --no-install to prevent implicit package downloads")
    if _git_is_destructive(tokens):
        return _deny("destructive or networked Git operations are not allowed")
    if any(token.lower() in _GENERIC_ESCAPE_ARGUMENTS for token in tokens[1:]):
        return _deny("command execution escape arguments are not allowed")

    if executable != "git" and executable_token == executable and executable in approved_wrappers:
        return _allow()
    if prefix_match is not None:
        return _allow()
    return _deny("command does not match an approved wrapper or command prefix")


def run_hook(policy_path: Path, raw_input: str) -> dict[str, str]:
    """Evaluate one hook input, converting every policy/input failure to deny."""
    try:
        payload = json.loads(raw_input)
        if not isinstance(payload, Mapping):
            raise ValueError("hook input must be a JSON object")
        wrappers, prefixes, write_scope_hint = _load_policy(policy_path)
        return evaluate_hook_payload(
            payload,
            approved_wrappers=wrappers,
            approved_command_prefixes=prefixes,
            write_scope_hint=write_scope_hint,
        )
    except Exception as exc:  # Hook boundaries must fail closed, including I/O errors.
        return _deny(f"hook policy unavailable: {type(exc).__name__}")


def to_claude_hook_response(response: Mapping[str, Any]) -> dict[str, Any]:
    """Express one policy decision in Claude Code's PreToolUse schema.

    The decision is identical; only the wire format differs. Cursor reads
    ``permission``; Claude Code reads ``hookSpecificOutput.permissionDecision``.
    Emitting both keeps one policy evaluator for every runtime.
    """
    allowed = str(response.get("permission") or "") == "allow"
    reason = str(response.get("agent_message") or "")
    return {
        **response,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow" if allowed else "deny",
            "permissionDecisionReason": reason or "approved by Axon sandbox policy",
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    policy_path = Path(arguments[0]) if len(arguments) == 1 else Path("")
    response = run_hook(policy_path, sys.stdin.read()) if arguments else _deny(
        "hook policy path is required"
    )
    payload = to_claude_hook_response(response)
    sys.stdout.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
