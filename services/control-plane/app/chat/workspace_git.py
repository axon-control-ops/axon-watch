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


def git_working_tree_is_clean(status_output: str) -> bool:
    """True when ``git status --short --branch`` shows only the branch header."""
    lines = [line.strip() for line in status_output.splitlines() if line.strip()]
    if not lines:
        return True
    file_status_lines = [line for line in lines if not line.startswith("##")]
    return not file_status_lines


def git_add_all(workspace_id: str) -> GitCommandResult:
    return run_git(workspace_id, ["git", "add", "-A"])


def git_commit(workspace_id: str, message: str) -> GitCommandResult:
    cleaned = message.strip()
    if not cleaned:
        cleaned = "Update via Axon-X"
    return run_git(workspace_id, ["git", "commit", "-m", cleaned])


def git_push(workspace_id: str) -> GitCommandResult:
    return run_git(workspace_id, ["git", "push"])


def derive_commit_message(workspace_id: str) -> str:
    """Build a descriptive commit subject from pending changes when none was given."""
    files: list[str] = []
    for args in (
        ["git", "diff", "--name-only", "HEAD"],
        ["git", "diff", "--name-only", "--cached"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ):
        result = run_git(workspace_id, args)
        if not result.success or result.output in {"", "(no output)"}:
            continue
        for line in result.output.splitlines():
            cleaned = line.strip()
            if cleaned:
                files.append(cleaned)

    files = list(dict.fromkeys(files))
    if not files:
        return "Update via Axon-X"

    blob = " ".join(files).lower()
    themes: list[str] = []
    if any(token in blob for token in ("kairo", "voice", "narration", "spoken")):
        themes.append("KAIRO voice")
    if any(token in blob for token in ("terminal", "xterm", "websocket")):
        themes.append("IDE terminal")
    if any(token in blob for token in ("explorer", "file-tree", "file_tree", "workspace-file")):
        themes.append("explorer")
    if any(token in blob for token in ("git_dispatch", "workspace_git", "lane_b_git")):
        themes.append("git dispatch")
    if any(token in blob for token in ("transcript", "conversation-seam")):
        themes.append("agent transcript")

    if themes:
        return f"Polish {', '.join(dict.fromkeys(themes))}"

    areas = sorted({path.split("/")[0] for path in files if "/" in path})
    if areas:
        return f"Update {'/'.join(areas[:2])} ({len(files)} files)"
    return f"Update {len(files)} workspace files"
