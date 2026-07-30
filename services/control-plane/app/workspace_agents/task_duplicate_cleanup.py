"""Cancel waiting Task Board tickets that duplicate completed (or twin) work.

Leads should not leave open clones of work that already finished — across
manual / semi / full. This runs after task completion and on Lead reconcile.
"""

from __future__ import annotations

from typing import Any

from app.persistence import task_store
from app.workspace_agents.task_goal_overlap import (
    goals_overlap,
    is_lead_follow_up_goal,
)

# Stricter than new-Lead-ask supersede — completion cleanup must not wipe
# intentional confirm/QA follow-through with only loose wording overlap.
_COMPLETE_OVERLAP = 0.62
_OPEN_CLONE_OVERLAP = 0.7


def _cancel_open_task(
    task_id: str,
    *,
    terminal_outcome: str,
) -> dict[str, Any] | None:
    try:
        row = task_store.cancel_task(task_id, terminal_outcome=terminal_outcome)
    except task_store.TaskLedgerError:
        return None
    run_id = str(row.get("run_id") or "").strip()
    if run_id:
        try:
            from app.runs.restart_reconcile import interrupt_run_on_restart

            interrupt_run_on_restart(run_id)
        except Exception:  # noqa: BLE001
            pass
    return row


def _candidate_blocked_by_dependency(
    candidate: dict[str, Any],
    *,
    completed_task_id: str,
) -> bool:
    deps = candidate.get("dependencies") or []
    if not isinstance(deps, list):
        return False
    return completed_task_id in {str(item).strip() for item in deps if str(item).strip()}


def cancel_waiting_duplicates_of_completed_task(
    completed: dict[str, Any],
    *,
    overlap_threshold: float = _COMPLETE_OVERLAP,
) -> list[dict[str, Any]]:
    """Cancel open tasks that would redo a just-completed ticket."""
    completed_id = str(completed.get("task_id") or "").strip()
    workspace_id = str(completed.get("workspace_id") or "").strip()
    completed_goal = str(completed.get("goal") or "")
    completed_role = str(completed.get("owner_role") or "").strip().lower()
    if not completed_id or not workspace_id or not completed_goal:
        return []
    if str(completed.get("status") or "").strip().lower() != "completed":
        return []

    cancelled: list[dict[str, Any]] = []
    for record in task_store.list_tasks(workspace_id=workspace_id, status="open", limit=500):
        task_id = str(record.get("task_id") or "").strip()
        if not task_id or task_id == completed_id:
            continue
        if _candidate_blocked_by_dependency(record, completed_task_id=completed_id):
            continue
        candidate_goal = str(record.get("goal") or "")
        # Lead follow-ups after a specialist are next-step work, not clones of
        # the specialist ticket — unless the follow-up itself is a twin of a
        # completed Lead follow-up (same role lead + overlap).
        if is_lead_follow_up_goal(candidate_goal) and not is_lead_follow_up_goal(
            completed_goal
        ):
            continue
        candidate_role = str(record.get("owner_role") or "").strip().lower()
        if completed_role and candidate_role and completed_role != candidate_role:
            continue
        if not goals_overlap(
            completed_goal,
            candidate_goal,
            threshold=overlap_threshold,
        ):
            continue
        row = _cancel_open_task(
            task_id,
            terminal_outcome=(
                f"superseded — duplicate of completed {completed_id}"
            ),
        )
        if row is not None:
            cancelled.append(row)
    return cancelled


def cancel_open_clone_duplicates(
    *,
    workspace_id: str,
    overlap_threshold: float = _OPEN_CLONE_OVERLAP,
) -> list[dict[str, Any]]:
    """Among open tickets, keep the newest twin and cancel older clones."""
    workspace = workspace_id.strip()
    if not workspace:
        return []
    open_tasks = task_store.list_tasks(workspace_id=workspace, status="open", limit=500)
    # Newest first — tie-break on created_at / task_id so clones with the same
    # second-resolution timestamp still keep a deterministic survivor.
    open_tasks = sorted(
        open_tasks,
        key=lambda row: (
            str(row.get("updated_at") or ""),
            str(row.get("created_at") or ""),
            str(row.get("task_id") or ""),
        ),
        reverse=True,
    )
    keep_ids: set[str] = set()
    cancelled: list[dict[str, Any]] = []
    for index, record in enumerate(open_tasks):
        task_id = str(record.get("task_id") or "").strip()
        if not task_id or task_id in keep_ids:
            continue
        goal = str(record.get("goal") or "")
        role = str(record.get("owner_role") or "").strip().lower()
        if is_lead_follow_up_goal(goal):
            # Only collapse identical Lead follow-up twins, never against specialists.
            twin_scope = "lead_follow_up"
        else:
            twin_scope = "specialist"
        keep_ids.add(task_id)
        for other in open_tasks[index + 1 :]:
            other_id = str(other.get("task_id") or "").strip()
            if not other_id or other_id in keep_ids:
                continue
            other_goal = str(other.get("goal") or "")
            other_role = str(other.get("owner_role") or "").strip().lower()
            if role and other_role and role != other_role:
                continue
            other_is_follow = is_lead_follow_up_goal(other_goal)
            if twin_scope == "lead_follow_up" and not other_is_follow:
                continue
            if twin_scope == "specialist" and other_is_follow:
                continue
            if _candidate_blocked_by_dependency(other, completed_task_id=task_id):
                continue
            if _candidate_blocked_by_dependency(record, completed_task_id=other_id):
                continue
            if not goals_overlap(goal, other_goal, threshold=overlap_threshold):
                continue
            row = _cancel_open_task(
                other_id,
                terminal_outcome=f"superseded — open clone of {task_id}",
            )
            if row is not None:
                cancelled.append(row)
    return cancelled


def reconcile_workspace_waiting_duplicates(
    *,
    workspace_id: str,
) -> dict[str, Any]:
    """Lead Task Board reconcile: drop waiting work already done or duplicated.

    Safe for manual / semi / full — only cancels **open** Waiting tickets.
    """
    workspace = workspace_id.strip()
    if not workspace:
        return {
            "workspace_id": "",
            "cancelled_vs_completed": [],
            "cancelled_open_clones": [],
        }

    cancelled_vs_completed: list[dict[str, Any]] = []
    seen_cancelled: set[str] = set()
    for completed in task_store.list_tasks(
        workspace_id=workspace, status="completed", limit=200
    ):
        for row in cancel_waiting_duplicates_of_completed_task(completed):
            task_id = str(row.get("task_id") or "").strip()
            if task_id and task_id not in seen_cancelled:
                seen_cancelled.add(task_id)
                cancelled_vs_completed.append(row)

    cancelled_open_clones = cancel_open_clone_duplicates(workspace_id=workspace)
    return {
        "workspace_id": workspace,
        "cancelled_vs_completed": cancelled_vs_completed,
        "cancelled_open_clones": cancelled_open_clones,
        "cancelled_count": len(cancelled_vs_completed) + len(cancelled_open_clones),
    }


def cleanup_after_task_completed(completed: dict[str, Any]) -> list[dict[str, Any]]:
    """Best-effort hook for complete_task call sites."""
    try:
        return cancel_waiting_duplicates_of_completed_task(completed)
    except Exception:  # noqa: BLE001 — never block completion
        return []


__all__ = [
    "cancel_open_clone_duplicates",
    "cancel_waiting_duplicates_of_completed_task",
    "cleanup_after_task_completed",
    "reconcile_workspace_waiting_duplicates",
]
