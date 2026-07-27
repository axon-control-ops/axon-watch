"""Shell/terminal transcript block helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


TERMINAL_PREVIEW_MAX_CHARS = 12_000
TERMINAL_PREVIEW_HEAD_CHARS = 8_000
TERMINAL_PREVIEW_TAIL_CHARS = 3_500


def terminal_output_preview(output: str) -> str:
    """Bound transcript output while retaining useful command head/tail receipts."""
    trimmed = output.strip()
    if len(trimmed) <= TERMINAL_PREVIEW_MAX_CHARS:
        return trimmed
    omitted = len(trimmed) - TERMINAL_PREVIEW_HEAD_CHARS - TERMINAL_PREVIEW_TAIL_CHARS
    marker = (
        f"… [{omitted:,} characters compacted to keep the IDE responsive; "
        "showing output head and tail] …"
    )
    return (
        f"{trimmed[:TERMINAL_PREVIEW_HEAD_CHARS].rstrip()}\n\n"
        f"{marker}\n\n"
        f"{trimmed[-TERMINAL_PREVIEW_TAIL_CHARS:].lstrip()}"
    )


def _relative_path(path: str, workspace_root: str) -> str:
    path = path.strip()
    if not path:
        return path

    root = Path(workspace_root).expanduser().resolve() if workspace_root else None
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        return path.lstrip("./")

    try:
        resolved = candidate.resolve()
    except OSError:
        resolved = candidate

    if root is not None:
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            pass
        basename = resolved.name
        if basename:
            if (root / basename).is_file():
                return basename
            if (root / "assets" / basename).is_file():
                return f"assets/{basename}"
            # Outside the workspace: keep the absolute path so Lane B edit
            # receipts remain verifiable (basename-only collapses cause false
            # "missing on disk" notices when agents edit elsewhere).
            return resolved.as_posix()

    parts = resolved.as_posix().split("/")
    if "README.md" in parts:
        return "README.md"
    return resolved.as_posix() if resolved.is_absolute() else (resolved.name or path)


def shell_output_from_result(result: Any) -> str:
    """Best-effort extraction of command output from a shell tool result."""
    if not isinstance(result, dict):
        return ""
    for container in (result.get("success"), result):
        if not isinstance(container, dict):
            continue
        # Cursor's interleaved output is the complete ordered stream. Prefer it
        # outright so separately populated stdout/stderr are not repeated.
        interleaved = container.get("interleavedOutput")
        if isinstance(interleaved, str) and interleaved.strip():
            return interleaved.rstrip()
        parts: list[str] = []
        seen: set[str] = set()
        for key in ("stdout", "output", "stderr"):
            value = container.get(key)
            if not isinstance(value, str):
                continue
            trimmed = value.rstrip()
            if not trimmed or trimmed in seen:
                continue
            seen.add(trimmed)
            parts.append(trimmed)
        if parts:
            return "\n".join(parts)
    return ""


_SHELL_TOOL_KEYS = ("shellToolCall", "runTerminalCommandToolCall", "terminalToolCall")


def shell_command_from_tool_call(tool_call: dict[str, Any]) -> str:
    for shell_key in _SHELL_TOOL_KEYS:
        shell_call = tool_call.get(shell_key)
        if not isinstance(shell_call, dict):
            continue
        args = shell_call.get("args") if isinstance(shell_call.get("args"), dict) else {}
        command = str(args.get("command") or args.get("commandLine") or "").strip()
        if command:
            return command
    return ""


def shell_description_from_tool_call(tool_call: dict[str, Any]) -> str:
    for shell_key in _SHELL_TOOL_KEYS:
        shell_call = tool_call.get(shell_key)
        if not isinstance(shell_call, dict):
            continue
        args = shell_call.get("args") if isinstance(shell_call.get("args"), dict) else {}
        description = str(args.get("description") or shell_call.get("description") or "").strip()
        if description:
            return description
    return ""


def shell_call_from_tool_call(tool_call: dict[str, Any]) -> dict[str, Any] | None:
    for shell_key in _SHELL_TOOL_KEYS:
        shell_call = tool_call.get(shell_key)
        if isinstance(shell_call, dict):
            return shell_call
    return None


def terminal_block(command: str, output: str) -> str:
    trimmed = terminal_output_preview(output)
    body = f"\n{trimmed}\n" if trimmed else "\n"
    return f"\n:::terminal {command}{body}:::\n"


def terminal_started_block(command: str, description: str = "") -> str:
    trimmed = command.strip()
    if not trimmed:
        return ""
    detail = description.strip()
    if detail:
        return f"\n:::terminal {trimmed}\n# {detail}\n"
    return f"\n:::terminal {trimmed}\n"


def terminal_close_body(output: str) -> str:
    trimmed = terminal_output_preview(output)
    if trimmed:
        return f"{trimmed}\n:::\n"
    return ":::\n"


def terminal_started_block_from_event(event: dict[str, Any]) -> str:
    """Open a live `:::terminal` block when a shell tool call starts (Cursor parity)."""
    if event.get("type") != "tool_call" or event.get("subtype") != "started":
        return ""
    tool_call = event.get("tool_call")
    if not isinstance(tool_call, dict):
        return ""
    return terminal_started_block(
        shell_command_from_tool_call(tool_call),
        shell_description_from_tool_call(tool_call),
    )


def shell_completion_from_event(event: dict[str, Any]) -> tuple[str, str] | None:
    if event.get("type") != "tool_call" or event.get("subtype") != "completed":
        return None
    tool_call = event.get("tool_call")
    if not isinstance(tool_call, dict):
        return None
    shell_call = shell_call_from_tool_call(tool_call)
    if shell_call is None:
        return None
    command = shell_command_from_tool_call(tool_call)
    if not command:
        return None
    output = shell_output_from_result(shell_call.get("result"))
    return command, output
