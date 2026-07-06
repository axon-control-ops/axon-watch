"""Bounded git subprocess execution inside workspace roots."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root

MAX_OUTPUT_CHARS = 1500
_GIT_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class GitCommandResult:
    args: list[str]
    success: bool
    output: str
    receipt_summary: str


def _truncate_output(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return f"{text[: MAX_OUTPUT_CHARS - 3].rstrip()}..."


def run_git(workspace_id: str, args: list[str]) -> GitCommandResult:
    normalized_args = [str(item).strip() for item in args if str(item).strip()]
    if not normalized_args or normalized_args[0] != "git":
        raise ValueError("git args must start with git")

    try:
        root = resolve_workspace_root(workspace_id)
    except WorkspaceRootError as exc:
        return GitCommandResult(
            args=normalized_args,
            success=False,
            output=_truncate_output(str(exc)),
            receipt_summary="Git command failed",
        )

    try:
        completed = subprocess.run(
            normalized_args,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        return GitCommandResult(
            args=normalized_args,
            success=False,
            output=_truncate_output("git executable not found on PATH"),
            receipt_summary="Git command failed",
        )
    except subprocess.TimeoutExpired:
        return GitCommandResult(
            args=normalized_args,
            success=False,
            output=_truncate_output(f"git timed out after {_GIT_TIMEOUT_SECONDS}s"),
            receipt_summary="Git command failed",
        )
    except OSError as exc:
        return GitCommandResult(
            args=normalized_args,
            success=False,
            output=_truncate_output(str(exc)),
            receipt_summary="Git command failed",
        )

    combined = "\n".join(
        part.strip()
        for part in (completed.stdout, completed.stderr)
        if part.strip()
    )
    output = combined or "(no output)"
    success = completed.returncode == 0
    command_label = " ".join(normalized_args[1:] or normalized_args)
    return GitCommandResult(
        args=normalized_args,
        success=success,
        output=_truncate_output(output),
        receipt_summary=f"git {command_label} succeeded" if success else f"git {command_label} failed",
    )


def git_status(workspace_id: str) -> GitCommandResult:
    return run_git(workspace_id, ["git", "status", "--short", "--branch"])


def git_add_all(workspace_id: str) -> GitCommandResult:
    return run_git(workspace_id, ["git", "add", "-A"])


def git_commit(workspace_id: str, message: str) -> GitCommandResult:
    cleaned = message.strip()
    if not cleaned:
        cleaned = "Update via Axon-X"
    return run_git(workspace_id, ["git", "commit", "-m", cleaned])


def git_push(workspace_id: str) -> GitCommandResult:
    return run_git(workspace_id, ["git", "push"])
