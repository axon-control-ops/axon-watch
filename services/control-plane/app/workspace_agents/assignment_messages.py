"""Human-readable assignment cards for employee IDE threads."""

from __future__ import annotations

import re
from typing import Any


_TASK_ID_RE = re.compile(r"\btask-[a-z0-9]{12,}\b", re.I)
_ROLE_PREFIX_RE = re.compile(r"^\[(?P<role>[a-z _-]+)\]\s*", re.I)


def employee_display_name(employee: dict[str, Any] | None, role: str) -> str:
    name = str((employee or {}).get("name") or "").strip()
    if name:
        return name
    cleaned = str(role or "").strip().replace("_", " ").replace("-", " ")
    return cleaned.title() if cleaned else "Agent"


def role_label(role: str) -> str:
    cleaned = str(role or "").strip().replace("_", " ").replace("-", " ")
    return cleaned.title() if cleaned else "Agent"


def readable_goal(goal: str, *, max_chars: int = 260) -> str:
    text = " ".join(str(goal or "").split()).strip()
    text = _ROLE_PREFIX_RE.sub("", text).strip()
    text = text.replace("Review and report on:", "").strip()
    text = _TASK_ID_RE.sub("the assigned task", text)
    text = re.sub(r"\s+", " ", text).strip(" -—:;")
    if not text:
        return "Complete the assigned work and report back with verification."
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 1].rstrip()}…"


def assignment_card(
    *,
    assignee_name: str,
    assignee_role: str,
    goal: str,
    task_id: str,
    run_id: str,
    state: str,
    lead_name: str | None = None,
    expected_files: list[str] | None = None,
    validation_status: str | None = None,
    commit_hash: str | None = None,
) -> str:
    action = "started work on" if state == "started" else "queued"
    role = str(assignee_role or "").strip().lower()
    status_subject = (
        "the Lead should decide, assign, escalate, or report back with receipts"
        if role == "lead"
        else "the specialist should implement, verify, and report back with receipts"
    )
    title = (
        f"{assignee_name} started this {role_label(assignee_role)} assignment."
        if state == "started"
        else f"{lead_name or 'Lead'} queued a {role_label(assignee_role)} assignment for {assignee_name}."
    )
    expected = ", ".join(str(item).strip() for item in (expected_files or []) if str(item).strip())
    return "\n".join(
        [
            title,
            "",
            f"Assigned to: {assignee_name} ({role_label(assignee_role)})",
            f"Task ID: {task_id}",
            f"Assignment: {readable_goal(goal)}",
            f"Objective: {readable_goal(goal)}",
            f"Expected files: {expected or 'role/task scoped files'}",
            f"Validation: {validation_status or 'pending'}",
            f"Commit: {commit_hash or 'pending'}",
            f"Status: {action}; {status_subject}.",
            f"Receipt: {task_id} · {run_id}",
        ]
    )


__all__ = [
    "assignment_card",
    "employee_display_name",
    "readable_goal",
    "role_label",
]
