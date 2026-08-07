"""Direct git workflows for Full Access Lane B when Cursor CLI blocks git subprocesses."""

from __future__ import annotations

import re

from app.chat.workspace_git import (
    collect_changed_paths,
    derive_commit_message,
    git_add_all,
    git_add_paths,
    git_commit,
    git_push,
    git_status,
    git_working_tree_is_clean,
)
from app.cli_runtime.approval_gate import full_access_requested
from app.plain_text_to_instructions import prompt_requests_git_actions
from app.workspace_agents.execution_policy import AgentExecutionPolicy

_COMMIT_INTENT_RE = re.compile(
    r"\b(?:commit(?:\s+(?:these|my|the|all))?(?:\s+changes?)?(?:\s+and\s+push)?"
    r"|create\s+(?:a\s+)?commit|git\s+commit)\b",
    re.IGNORECASE,
)
_COMMIT_ALL_RE = re.compile(r"\bcommit\s+all\b", re.IGNORECASE)
_PUSH_INTENT_RE = re.compile(r"\bpush\b", re.IGNORECASE)
# "commit first and then <work>" / "commit, then <work>" — commit, then continue.
_COMMIT_THEN_RE = re.compile(
    r"^\s*(?:please\s+)?commit(?:\s+first)?(?:\s+(?:these|my|the|all))?(?:\s+changes?)?"
    r"(?:\s+and\s+push)?\s*(?:[,.]?\s*|\s+)(?:and\s+)?(?:then|afterwards|after\s+that)\b\s*[:,\-]?\s*",
    re.IGNORECASE,
)
_PATH_TOKEN_RE = re.compile(
    r"(?:^|[\s`\"'(])((?:[\w.-]+/)*[\w.-]+\.(?:py|ts|tsx|vue|js|jsx|md|json|css|html|sh))\b"
)
# Interrogative prompts ("did you commit and push?") are questions, not
# instructions — they must go to the runtime for an answer, never execute git.
_QUESTION_RE = re.compile(
    r"^\s*(?:did|do|does|have|has|had|is|are|was|were|can|could|will|would|"
    r"should|shall|what|when|where|which|who|why|how)\b",
    re.IGNORECASE,
)
_COMMIT_MESSAGE_PATTERNS = (
    re.compile(r'commit(?:\s+message)?[\s:=-]+["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'git\s+commit\s+-m\s+["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'-m\s+["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'(?:with|using)\s+(?:message|msg)[\s:=-]+["\']([^"\']+)["\']', re.IGNORECASE),
)

_MIXED_TREE_FILE_FLOOR = 15
_MIXED_TREE_TOP_FLOOR = 3


def _is_question(prompt: str) -> bool:
    stripped = prompt.strip()
    if stripped.endswith("?"):
        return True
    if re.search(r"\b(?:asking if|asked if|asking whether|i was asking)\b", stripped, re.IGNORECASE):
        return True
    return bool(_QUESTION_RE.match(stripped))


def split_commit_then_remainder(prompt: str) -> str | None:
    """If prompt is ``commit … then <rest>``, return ``<rest>``; else None."""
    match = _COMMIT_THEN_RE.match(prompt.strip())
    if not match:
        return None
    remainder = prompt.strip()[match.end() :].strip(" :\n\t-")
    return remainder or None


def _extract_commit_message(prompt: str) -> str | None:
    for pattern in _COMMIT_MESSAGE_PATTERNS:
        match = pattern.search(prompt)
        if match:
            message = match.group(1).strip()
            if message:
                return message
    return None


def _terminal_receipt(command: str, output: str) -> str:
    body = (output or "").rstrip() or "(no output)"
    return f":::terminal {command}\n{body}\n:::"


def _paths_mentioned_in_prompt(prompt: str, changed: list[str]) -> list[str]:
    tokens = [match.group(1) for match in _PATH_TOKEN_RE.finditer(prompt)]
    if not tokens:
        return []
    selected: list[str] = []
    for path in changed:
        base = path.rsplit("/", 1)[-1]
        if path in tokens or base in tokens:
            selected.append(path)
            continue
        if any(path.endswith(token) or path == token for token in tokens):
            selected.append(path)
    return list(dict.fromkeys(selected))


def _mixed_tree_needs_explicit_scope(changed: list[str]) -> bool:
    if len(changed) < _MIXED_TREE_FILE_FLOOR:
        return False
    tops = {path.split("/", 1)[0] for path in changed if "/" in path}
    return len(tops) >= _MIXED_TREE_TOP_FLOOR


def resolve_stage_plan(
    *,
    workspace_id: str,
    user_prompt: str,
    continue_prompt: str | None,
) -> tuple[list[str] | None, str | None]:
    """Return ``(paths|None for -A, refusal_message|None)``."""
    changed = collect_changed_paths(workspace_id)
    if not changed:
        return None, None

    mentioned = _paths_mentioned_in_prompt(user_prompt, changed)
    if mentioned:
        return mentioned, None

    # The mixed-tree guard below used to only run for "commit … then …"
    # continuation turns — a plain "commit and push" (the common phrasing,
    # `continue_prompt is None`) skipped straight to a blind `git add -A`.
    # That let one task's commit sweep up whatever unrelated, concurrent
    # agent's dirty files happened to be sitting in the same workspace root
    # at that moment. Apply the same guard to every commit turn instead.
    explicit_commit_all = bool(_COMMIT_ALL_RE.search(user_prompt))
    if explicit_commit_all:
        return None, None

    if _mixed_tree_needs_explicit_scope(changed):
        tops = sorted({path.split("/", 1)[0] for path in changed if "/" in path})
        sample = ", ".join(changed[:5])
        more = f" (+{len(changed) - 5} more)" if len(changed) > 5 else ""
        return [], (
            "Working tree spans multiple areas "
            f"({', '.join(tops[:5])}; {len(changed)} files). "
            "I will not run a blind `git add -A` when this much is pending — "
            "some of it may belong to other concurrent work. "
            "Reply with `commit all and then …`, or name paths to stage "
            f"(pending includes: {sample}{more})."
        )
    return None, None


def try_lane_b_git_commit_dispatch(
    *,
    workspace_id: str,
    user_prompt: str,
    execution_access: str | None,
    execution_policy: AgentExecutionPolicy | None = None,
) -> dict[str, object] | None:
    if not full_access_requested(execution_access):
        return None
    if _is_question(user_prompt):
        return None
    if not prompt_requests_git_actions(user_prompt):
        return None

    # execution_access above is the OPERATOR's own Full Access toggle — it says
    # nothing about which employee's thread this turn is dispatched under. A
    # chat message that lands in a consultative-only role's thread (e.g.
    # watcher: write_paths=(), execution_access="consultative") must not run a
    # real `git add`/`commit`/`push` just because the operator's own toggle is
    # on; that role is never allowed to write, regardless of who is asking.
    if execution_policy is not None and execution_policy.execution_access != "full":
        return {
            "content": (
                "This teammate's role is consultative-only and has no write scope "
                "— I can't run git add/commit/push here regardless of Full Access. "
                "Ask a role with write access (Lead/Frontend/Backend/Integrations) "
                "to make this commit, or do it from a thread bound to one of those roles."
            ),
            "dispatched": False,
            "continue_prompt": None,
            "execution_tier": "executing",
            "runtime_id": "workspace_git",
            "runtime_label": "workspace git",
            "reason": "role execution_access is not full",
        }

    continue_prompt = split_commit_then_remainder(user_prompt)
    subject_source = continue_prompt or user_prompt
    explicit_message = _extract_commit_message(user_prompt)
    status = git_status(workspace_id)
    lines = [
        "Running git through the Axon-X control plane (Cursor CLI blocks git subprocesses).",
        "",
        _terminal_receipt("git status", status.output),
    ]

    if not status.success:
        return {
            "content": "\n".join(lines),
            "dispatched": True,
            "continue_prompt": None,
            "execution_tier": "executing",
            "runtime_id": "workspace_git",
            "runtime_label": "workspace git",
            "reason": status.receipt_summary,
        }

    if git_working_tree_is_clean(status.output):
        lines.extend(
            [
                "",
                "Nothing to commit — the working tree is clean.",
            ]
        )
        return {
            "content": "\n".join(lines),
            # Clean tree is not a failure — still continue the remainder when present.
            "dispatched": True,
            "continue_prompt": continue_prompt,
            "execution_tier": "executing",
            "runtime_id": "workspace_git",
            "runtime_label": "workspace git",
            "reason": "clean working tree",
        }

    stage_paths, stage_refusal = resolve_stage_plan(
        workspace_id=workspace_id,
        user_prompt=user_prompt,
        continue_prompt=continue_prompt,
    )
    if stage_refusal:
        lines.extend(["", stage_refusal])
        return {
            "content": "\n".join(lines),
            "dispatched": False,
            "continue_prompt": None,
            "execution_tier": "executing",
            "runtime_id": "workspace_git",
            "runtime_label": "workspace git",
            "reason": "mixed working tree requires explicit scope",
        }

    message = explicit_message or derive_commit_message(
        workspace_id,
        turn_subject=subject_source,
        # None means "git add -A" (whole tree is genuinely the change); a
        # concrete list means only those paths are being staged, so the
        # subject must describe just them, not everything sitting dirty.
        scoped_paths=stage_paths,
    )
    if not message.strip() or message.strip() == "Update via Axon-X":
        lines.extend(
            [
                "",
                "I need an explicit commit message before I can commit these changes.",
                'Reply with something like: `commit with message "Your subject here"`.',
            ]
        )
        return {
            "content": "\n".join(lines),
            "dispatched": False,
            "continue_prompt": None,
            "execution_tier": "executing",
            "runtime_id": "workspace_git",
            "runtime_label": "workspace git",
            "reason": "commit message required",
        }

    if stage_paths is None:
        staged = git_add_all(workspace_id)
        stage_label = "git add -A"
    else:
        staged = git_add_paths(workspace_id, stage_paths)
        stage_label = "git add -- " + " ".join(stage_paths[:8])
        if len(stage_paths) > 8:
            stage_label += f" (+{len(stage_paths) - 8} more)"
    lines.extend(
        [
            "",
            _terminal_receipt(stage_label, staged.output or "(staged)"),
        ]
    )
    if not staged.success:
        return {
            "content": "\n".join(lines),
            "dispatched": True,
            "continue_prompt": None,
            "execution_tier": "executing",
            "runtime_id": "workspace_git",
            "runtime_label": "workspace git",
            "reason": staged.receipt_summary,
        }

    committed = git_commit(workspace_id, message)
    lines.extend(
        [
            "",
            _terminal_receipt(f'git commit -m "{message}"', committed.output),
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
                _terminal_receipt("git push", pushed.output),
            ]
        )
        if pushed.success:
            summary += " Pushed to the remote."
        else:
            summary += f" Push failed: {pushed.receipt_summary}"

    return {
        "content": f"{summary}\n\n" + "\n".join(lines),
        "dispatched": committed.success,
        # Only continue the remainder when the commit (or clean-tree noop) succeeded.
        "continue_prompt": continue_prompt if committed.success else None,
        "execution_tier": "executing",
        "runtime_id": "workspace_git",
        "runtime_label": "workspace git",
        "reason": committed.receipt_summary,
    }
