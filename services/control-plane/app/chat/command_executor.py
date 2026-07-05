"""Bounded workspace command execution for operator chat dispatch."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import urlopen

from app.chat.command_intent import classify_command
from app.runs.service import RunLifecycleError, list_pending_review_runs, resume_run
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root
from app.workspace_files import WorkspaceFileError, list_workspace_files, read_workspace_file

MAX_OUTPUT_CHARS = 1500
_READ_PREFIX = re.compile(r"^(?:read|cat)\s+(.+)$", re.IGNORECASE)
_GIT_STATUS_PREFIX = re.compile(r"^git\s+status\b", re.IGNORECASE)
_RESUME_FROM_REVIEW = re.compile(
    r"^(?:resume(?:\s+from)?(?:\s+review|\s+review-ready)|resume-from-review)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CommandExecutionResult:
    intent: str
    success: bool
    output: str
    receipt_summary: str
    run_id: str | None = None



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


def execute_git_status(workspace_id: str) -> CommandExecutionResult:
    try:
        root = resolve_workspace_root(workspace_id)
        completed = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        combined = "\n".join(
            part.strip()
            for part in (completed.stdout, completed.stderr)
            if part.strip()
        )
        output = combined or "(no output)"
        success = completed.returncode == 0
        return CommandExecutionResult(
            intent="git_status",
            success=success,
            output=_truncate_output(output),
            receipt_summary="Git status succeeded" if success else "Git status failed",
        )
    except FileNotFoundError:
        return CommandExecutionResult(
            intent="git_status",
            success=False,
            output=_truncate_output("git executable not found on PATH"),
            receipt_summary="Git status failed",
        )
    except (WorkspaceRootError, OSError, subprocess.TimeoutExpired) as exc:
        return CommandExecutionResult(
            intent="git_status",
            success=False,
            output=_truncate_output(str(exc)),
            receipt_summary="Git status failed",
        )


def _primary_review_ready_run(workspace_id: str) -> dict[str, object] | None:
    review_runs = [
        record
        for record in list_pending_review_runs()
        if record.get("workspace_id") == workspace_id
    ]
    if not review_runs:
        return None
    return review_runs[-1]


def execute_resume_from_review(workspace_id: str) -> CommandExecutionResult:
    target = _primary_review_ready_run(workspace_id)
    if target is None:
        return CommandExecutionResult(
            intent="resume_from_review",
            success=False,
            output=_truncate_output(
                f"No review_ready run found for workspace {workspace_id}."
            ),
            receipt_summary="Resume from review failed",
        )

    run_id = str(target["run_id"])
    try:
        resumed = resume_run(run_id)
    except RunLifecycleError as exc:
        return CommandExecutionResult(
            intent="resume_from_review",
            success=False,
            output=_truncate_output(str(exc)),
            receipt_summary="Resume from review failed",
            run_id=run_id,
        )

    return CommandExecutionResult(
        intent="resume_from_review",
        success=True,
        output=_truncate_output(
            f"Resumed {run_id} from review_ready to {resumed['phase']}.\n"
            f"{resumed.get('current_step') or 'Run resumed for follow-up work'}"
        ),
        receipt_summary=f"Resumed run {run_id} from review_ready",
        run_id=run_id,
    )


def execute_unsupported(content: str) -> CommandExecutionResult:
    hints = (
        "Supported commands in this slice:\n"
        "• health / api/health — probe control-plane health\n"
        "• ls / list files — list workspace files\n"
        "• read README.md / cat notes.txt — read a workspace file\n"
        "• git status — show git status in the workspace root\n"
        "• resume from review — resume the primary review_ready run"
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
    if intent == "git_status":
        return execute_git_status(workspace_id)
    if intent == "resume_from_review":
        return execute_resume_from_review(workspace_id)
    return execute_unsupported(content)
