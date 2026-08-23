"""Task scope-guard clause for the continuous worker prompt.

Split out of ``worker_prompt.py`` per its ratchet target ("split lead evidence
and task scope clauses next").
"""

from __future__ import annotations

import re

OUT_OF_SCOPE_GUARD_MARKER = "OUT_OF_SCOPE_GUARD:"


def task_scope_anchors(*parts: str, limit: int = 8) -> list[str]:
    anchors: list[str] = []
    seen: set[str] = set()
    for part in parts:
        text = str(part or "")
        candidates = re.findall(r"`([^`]+)`", text)
        candidates.extend(re.findall(r"\b[\w./-]*[./_-][\w./-]+\b", text))
        for raw in candidates:
            cleaned = str(raw).strip().strip(".,;:()[]{}")
            if not cleaned or len(cleaned) < 3:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            anchors.append(cleaned)
            if len(anchors) >= limit:
                return anchors
    return anchors


def task_scope_clause(
    *,
    goal: str,
    acceptance: str,
    allowed_paths: list[str] | None = None,
) -> str:
    paths = [str(p).strip() for p in (allowed_paths or []) if str(p).strip()]
    anchors = task_scope_anchors(goal, acceptance)
    anchor_clause = ""
    if paths:
        joined = ", ".join(f"`{path}`" for path in paths[:12])
        anchor_clause = (
            f" Explicit allowed write paths for this leased task: {joined}. "
            "Do not modify any path outside that allowlist."
        )
    elif anchors:
        joined = ", ".join(f"`{anchor}`" for anchor in anchors)
        anchor_clause = f" Hard scope anchors from the task: {joined}. "
    return (
        " Scope guard: before you browse, edit, or summarize anything, lock onto the "
        "leased task's exact goal and acceptance criteria."
        f"{anchor_clause}"
        "Only open, mention, or modify files and topics that directly serve that scope. "
        "Do not drift into neighboring files, similarly named campaigns, prior tasks, or "
        "semantically related artifacts just because they are nearby. "
        "If the goal is about a README, docs, layout, bug, API, or specific deliverable, "
        "treat unrelated posts, assets, illustrations, marketing copy, and old workspace "
        "tasks as out of scope unless the goal explicitly asks for them. "
        f"If the next file or topic is not clearly justified by the task, stop and reply "
        f"with `{OUT_OF_SCOPE_GUARD_MARKER} <file-or-topic> is not required for this leased task` "
        "instead of continuing."
    )


__all__ = [
    "OUT_OF_SCOPE_GUARD_MARKER",
    "task_scope_anchors",
    "task_scope_clause",
]
