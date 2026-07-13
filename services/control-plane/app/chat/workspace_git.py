"""Bounded git subprocess execution inside workspace roots."""

from __future__ import annotations

import re
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


_COMMIT_INTENT_ONLY_RE = re.compile(
    r"^\s*(?:please\s+)?(?:commit(?:\s+(?:these|my|the|all))?(?:\s+changes?)?"
    r"(?:\s+and\s+push)?|create\s+(?:a\s+)?commit|git\s+commit(?:\s+and\s+push)?)"
    r"(?:\s+please)?[.!]?\s*$",
    re.IGNORECASE,
)


def _normalize_turn_subject(turn_subject: str | None) -> str | None:
    """Use the operator/agent turn as commit subject when it describes real work."""
    text = " ".join(str(turn_subject or "").split()).strip()
    if not text:
        return None
    if _COMMIT_INTENT_ONLY_RE.match(text):
        return None
    # Drop trailing commit instructions glued onto a real subject.
    text = re.sub(
        r"(?:,?\s+)?(?:and\s+)?(?:please\s+)?(?:commit(?:\s+and\s+push)?|git\s+commit).*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" ,.-")
    if not text or _COMMIT_INTENT_ONLY_RE.match(text):
        return None
    if len(text) > 72:
        cut = text[:71].rsplit(" ", 1)[0].rstrip(" ,.-")
        text = f"{cut}…" if cut else f"{text[:71]}…"
    return text


def _collect_changed_paths(workspace_id: str) -> list[str]:
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
    return list(dict.fromkeys(files))


def _summarize_diff_stat(workspace_id: str, files: list[str]) -> str | None:
    """Build a subject from ``git diff --stat`` (+ untracked basenames)."""
    if not files:
        return None

    stat = run_git(workspace_id, ["git", "diff", "--stat", "HEAD"])
    cached = run_git(workspace_id, ["git", "diff", "--cached", "--stat"])
    stat_blob = "\n".join(
        part
        for part in (stat.output if stat.success else "", cached.output if cached.success else "")
        if part and part != "(no output)"
    )

    insert_total = 0
    delete_total = 0
    for match in re.finditer(r"(\d+)\s+insertions?\(\+\)", stat_blob):
        insert_total += int(match.group(1))
    for match in re.finditer(r"(\d+)\s+deletions?\(-\)", stat_blob):
        delete_total += int(match.group(1))

    basenames: list[str] = []
    for path in files:
        name = path.rsplit("/", 1)[-1]
        if name and name not in basenames:
            basenames.append(name)
        if len(basenames) >= 3:
            break

    if not basenames:
        return None

    if insert_total and not delete_total and all(
        path.startswith("apps/") or path.startswith("services/") or "/" in path for path in files
    ):
        # Prefer "Add" when the tree is mostly new files.
        untracked = run_git(workspace_id, ["git", "ls-files", "--others", "--exclude-standard"])
        untracked_set = {
            line.strip()
            for line in (untracked.output.splitlines() if untracked.success else [])
            if line.strip()
        }
        if files and all(path in untracked_set for path in files):
            verb = "Add"
        else:
            verb = "Update"
    elif delete_total and not insert_total:
        verb = "Remove"
    else:
        verb = "Update"

    focus = ", ".join(basenames[:2])
    if len(basenames) > 2 or len(files) > 2:
        focus = f"{focus} (+{len(files) - min(2, len(basenames))} more)" if len(files) > 2 else focus

    counts = ""
    if insert_total or delete_total:
        counts = f" (+{insert_total}/−{delete_total})"

    subject = f"{verb} {focus}{counts}".strip()
    if len(subject) > 72:
        subject = f"{subject[:71].rstrip()}…"
    return subject


def derive_commit_message(workspace_id: str, turn_subject: str | None = None) -> str:
    """Build a commit subject from the turn text and/or ``git diff --stat``.

    Preference order:
    1. Descriptive operator/agent turn subject (not bare "commit these changes")
    2. Diff-stat summary of pending paths
    3. Generic fallback
    """
    from_turn = _normalize_turn_subject(turn_subject)
    files = _collect_changed_paths(workspace_id)
    from_diff = _summarize_diff_stat(workspace_id, files)

    if from_turn and from_diff and from_turn.lower() not in from_diff.lower():
        # Keep the human intent when it already names the work.
        if any(token in from_turn.lower() for token in ("fix", "add", "update", "extract", "harden", "land")):
            return from_turn
    if from_diff:
        return from_diff
    if from_turn:
        return from_turn
    if files:
        areas = sorted({path.split("/")[0] for path in files if "/" in path})
        if areas:
            return f"Update {'/'.join(areas[:2])} ({len(files)} files)"
        return f"Update {len(files)} workspace files"
    return "Update via Axon-X"
