"""Bounded workspace shell execution for explicit `run …` operator commands."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root

MAX_OUTPUT_CHARS = 1500
_SHELL_TIMEOUT_SECONDS = 120
_RUN_PREFIX = re.compile(r"^run\s+(.+)$", re.IGNORECASE)

_BLOCKED_SHELL_PATTERNS = (
    r"\bsudo\b",
    r"\brm\s+-rf\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r"[|;&`]",
    r"\$\(",
    r">\s*[^\s]",
    r"<\(",
)


@dataclass(frozen=True)
class ShellCommandValidation:
    command_line: str
    ok: bool
    reason: str = ""


def extract_shell_command_line(content: str) -> str | None:
    match = _RUN_PREFIX.match(content.strip())
    if not match:
        return None
    return match.group(1).strip()


def validate_shell_command_line(command_line: str) -> ShellCommandValidation:
    normalized = command_line.strip()
    if not normalized:
        return ShellCommandValidation(command_line=normalized, ok=False, reason="empty command")

    for pattern in _BLOCKED_SHELL_PATTERNS:
        if re.search(pattern, normalized):
            return ShellCommandValidation(
                command_line=normalized,
                ok=False,
                reason="blocked shell pattern",
            )

    return ShellCommandValidation(command_line=normalized, ok=True)


def truncate_shell_output(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return f"{text[: MAX_OUTPUT_CHARS - 3].rstrip()}..."


def execute_shell_command(*, workspace_id: str, content: str) -> tuple[bool, str, str]:
    command_line = extract_shell_command_line(content)
    if command_line is None:
        return False, "", "shell command must start with run "

    validation = validate_shell_command_line(command_line)
    if not validation.ok:
        return False, "", f"shell command rejected: {validation.reason}"

    try:
        root = resolve_workspace_root(workspace_id)
    except WorkspaceRootError as exc:
        return False, "", str(exc)

    try:
        completed = subprocess.run(
            validation.command_line,
            shell=True,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=_SHELL_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        return False, "", "shell executable not found on PATH"
    except subprocess.TimeoutExpired:
        return False, "", f"shell command timed out after {_SHELL_TIMEOUT_SECONDS}s"
    except OSError as exc:
        return False, "", str(exc)

    combined = "\n".join(
        part.strip()
        for part in (completed.stdout, completed.stderr)
        if part.strip()
    )
    output = combined or "(no output)"
    success = completed.returncode == 0
    return success, truncate_shell_output(output), f"exit {completed.returncode}"
