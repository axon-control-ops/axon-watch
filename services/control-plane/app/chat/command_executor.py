"""Bounded workspace command execution for operator chat dispatch."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import urlopen

from app.workspace_files import WorkspaceFileError, list_workspace_files, read_workspace_file

MAX_OUTPUT_CHARS = 1500
_READ_PREFIX = re.compile(r"^(?:read|cat)\s+(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class CommandExecutionResult:
    intent: str
    success: bool
    output: str
    receipt_summary: str


def classify_command(content: str) -> str:
    lowered = content.strip().lower()
    if not lowered:
        return "unsupported"

    if any(token in lowered for token in ("health", "api/health", "runtime/summary")):
        return "health_probe"
    if lowered.startswith("ls") or "list files" in lowered or lowered == "dir":
        return "list_files"
    if _READ_PREFIX.match(content.strip()) or "readme" in lowered:
        return "read_file"
    return "unsupported"


def _truncate_output(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return f"{text[: MAX_OUTPUT_CHARS - 3].rstrip()}..."


def _control_plane_base_url() -> str:
    return os.environ.get("AXON_WATCH_CONTROL_PLANE_BASE_URL", "http://127.0.0.1:8787").rstrip("/")


def _extract_read_path(content: str) -> str:
    match = _READ_PREFIX.match(content.strip())
    if match:
        return match.group(1).strip()
    if "notes.txt" in content.lower():
        return "notes.txt"
    return "README.md"


def execute_health_probe() -> CommandExecutionResult:
    url = f"{_control_plane_base_url()}/api/health"
    try:
        with urlopen(url, timeout=3) as response:
            body = response.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
            output = json.dumps(payload, indent=2)
        except json.JSONDecodeError:
            output = body
        return CommandExecutionResult(
            intent="health_probe",
            success=True,
            output=_truncate_output(output),
            receipt_summary="Health probe succeeded",
        )
    except (URLError, OSError, TimeoutError) as exc:
        return CommandExecutionResult(
            intent="health_probe",
            success=False,
            output=_truncate_output(f"health probe failed: {exc}"),
            receipt_summary="Health probe failed",
        )


def execute_list_files(workspace_id: str) -> CommandExecutionResult:
    try:
        files = list_workspace_files(workspace_id)
        if not files:
            output = "(no files)"
        else:
            lines = [f"{item['path']} ({item['size_bytes']} bytes)" for item in files]
            output = "\n".join(lines)
        return CommandExecutionResult(
            intent="list_files",
            success=True,
            output=_truncate_output(output),
            receipt_summary=f"Listed {len(files)} workspace file(s)",
        )
    except (WorkspaceFileError, OSError) as exc:
        return CommandExecutionResult(
            intent="list_files",
            success=False,
            output=_truncate_output(str(exc)),
            receipt_summary="Workspace file listing failed",
        )


def execute_read_file(workspace_id: str, content: str) -> CommandExecutionResult:
    path = _extract_read_path(content)
    try:
        payload = read_workspace_file(workspace_id, path)
        file_content = str(payload.get("content", ""))
        header = f"# {path}\n"
        return CommandExecutionResult(
            intent="read_file",
            success=True,
            output=_truncate_output(f"{header}{file_content}"),
            receipt_summary=f"Read workspace file {path}",
        )
    except (WorkspaceFileError, OSError) as exc:
        return CommandExecutionResult(
            intent="read_file",
            success=False,
            output=_truncate_output(str(exc)),
            receipt_summary=f"Failed to read {path}",
        )


def execute_unsupported(content: str) -> CommandExecutionResult:
    hints = (
        "Supported commands in this slice:\n"
        "• health / api/health — probe control-plane health\n"
        "• ls / list files — list workspace files\n"
        "• read README.md / cat notes.txt — read a workspace file"
    )
    return CommandExecutionResult(
        intent="unsupported",
        success=False,
        output=_truncate_output(f"Unsupported command: {content.strip()}\n\n{hints}"),
        receipt_summary="Unsupported operator command",
    )


def execute_command(*, workspace_id: str, content: str) -> CommandExecutionResult:
    intent = classify_command(content)
    if intent == "health_probe":
        return execute_health_probe()
    if intent == "list_files":
        return execute_list_files(workspace_id)
    if intent == "read_file":
        return execute_read_file(workspace_id, content)
    return execute_unsupported(content)
