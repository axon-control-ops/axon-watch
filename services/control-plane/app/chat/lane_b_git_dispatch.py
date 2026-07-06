"""Direct git workflows for Full Access Lane B when Cursor CLI blocks git subprocesses."""

from __future__ import annotations

import re

from app.chat.workspace_git import git_add_all, git_commit, git_push, git_status
from app.cli_runtime.approval_gate import full_access_requested

_COMMIT_INTENT_RE = re.compile(
    r"\b(?:commit(?:\s+(?:these|my|the|all))?(?:\s+changes?)?(?:\s+and\s+push)?"
    r"|create\s+(?:a\s+)?commit|git\s+commit)\b",
    re.IGNORECASE,
)
_PUSH_INTENT_RE = re.compile(r"\bpush\b", re.IGNORECASE)
_COMMIT_MESSAGE_PATTERNS = (
    re.compile(r'commit(?:\s+message)?[\s:=-]+["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'git\s+commit\s+-m\s+["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'-m\s+["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'(?:with|using)\s+(?:message|msg)[\s:=-]+["\']([^"\']+)["\']', re.IGNORECASE),
)


def _extract_commit_message(prompt: str) -> str | None:
    for pattern in _COMMIT_MESSAGE_PATTERNS:
        match = pattern.search(prompt)
        if match:
            message = match.group(1).strip()
            if message:
                return message
    return None


def try_lane_b_git_commit_dispatch(
    *,
    workspace_id: str,
    user_prompt: str,
    execution_access: str | None,
) -> dict[str, object] | None:
    if not full_access_requested(execution_access):
        return None
    if not _COMMIT_INTENT_RE.search(user_prompt):
        return None

    message = _extract_commit_message(user_prompt) or "Update via Axon-X"
    status = git_status(workspace_id)
    lines = [
        "Running git through the Axon-X control plane (Cursor CLI blocks git subprocesses).",
        "",
        f"**git status**\n```\n{status.output}\n```",
    ]

    if not status.success:
        return {
            "content": "\n".join(lines),
            "dispatched": True,
            "runtime_id": "workspace_git",
            "runtime_label": "workspace git",
            "reason": status.receipt_summary,
        }

    if status.output.strip() in {"", "(no output)"}:
        lines.extend(
            [
                "",
                "Nothing to commit — the working tree is clean.",
            ]
        )
        return {
            "content": "\n".join(lines),
            "dispatched": True,
            "runtime_id": "workspace_git",
            "runtime_label": "workspace git",
            "reason": "clean working tree",
        }

    staged = git_add_all(workspace_id)
    lines.extend(
        [
            "",
            f"**git add -A**\n```\n{staged.output or '(staged)'}\n```",
        ]
    )
    if not staged.success:
        return {
            "content": "\n".join(lines),
            "dispatched": True,
            "runtime_id": "workspace_git",
            "runtime_label": "workspace git",
            "reason": staged.receipt_summary,
        }

    committed = git_commit(workspace_id, message)
    lines.extend(
        [
            "",
            f"**git commit -m \"{message}\"**\n```\n{committed.output}\n```",
        ]
    )
    if committed.success:
        summary = f"Committed successfully with message: {message}"
    else:
        summary = f"Commit failed: {committed.receipt_summary}"

    push_requested = bool(_PUSH_INTENT_RE.search(user_prompt))
    if committed.success and push_requested:
        pushed = git_push(workspace_id)
        lines.extend(
            [
                "",
                f"**git push**\n```\n{pushed.output}\n```",
            ]
        )
        if pushed.success:
            summary += " Pushed to the remote."
        else:
            summary += f" Push failed: {pushed.receipt_summary}"

    return {
        "content": f"{summary}\n\n" + "\n".join(lines),
        "dispatched": committed.success,
        "runtime_id": "workspace_git",
        "runtime_label": "workspace git",
        "reason": committed.receipt_summary,
    }
