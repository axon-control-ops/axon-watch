"""Operator-initiated start for a Waiting (open) task ledger row."""

from __future__ import annotations

from typing import Any

from app.persistence import task_store
from app.runs.service import append_run_execution_receipt, create_run
from app.workspace_agents.lead_fan_out import (
    _deps_completed,
    _post_assignment_to_employee_thread,
)


class OperatorStartTaskError(ValueError):
    """Domain error for operator Start on the Task Board."""


def operator_start_task(task_id: str) -> dict[str, Any]:
    """Lease an open task, queue a specialist run, and post the IDE assignment.

    Does not force Lane B dispatch — the continuous scheduler / Full Autonomy
    picks up queued leased work. Matches Lead fan-out assignment semantics.
    """
    cleaned = str(task_id or "").strip()
    if not cleaned:
        raise OperatorStartTaskError("task_id is required")

    task = task_store.get_task(cleaned)
    if task is None:
        raise OperatorStartTaskError(f"task not found: {cleaned}")

    status = str(task.get("status") or "").strip().lower()
    if status != "open":
        raise OperatorStartTaskError(
            f"only open/waiting tasks can be started (status={status or 'unknown'})"
        )

    if not _deps_completed(task):
        raise OperatorStartTaskError(
            "task is still blocked by unfinished dependencies"
        )

    workspace_id = str(task.get("workspace_id") or "").strip()
    owner_role = str(task.get("owner_role") or "").strip().lower() or "watcher"
    if not workspace_id:
        raise OperatorStartTaskError("task is missing workspace_id")

    holder = f"operator-start-{workspace_id}-{owner_role}"
    try:
        leased = task_store.lease_task(cleaned, lease_holder=holder)
    except task_store.TaskLedgerError as exc:
        raise OperatorStartTaskError(str(exc)) from exc

    goal = str(leased.get("goal") or task.get("goal") or "").strip()
    summary = f"{owner_role}: {goal[:120]}" if goal else f"{owner_role}: start {cleaned}"
    run = create_run(
        workspace_id=workspace_id,
        mode="agent",
        summary=summary,
        detail=f"Operator Start task={cleaned}",
        employee_role=owner_role,
        task_id=cleaned,
        require_leased_task=True,
        enter_execution=False,
    )
    run_id = str(run["run_id"])
    append_run_execution_receipt(
        run_id,
        receipt_type="operator_task_started",
        receipt_summary=f"Operator started {owner_role} task {cleaned}",
        actor="operator",
    )
    thread_id = _post_assignment_to_employee_thread(
        workspace_id=workspace_id,
        owner_role=owner_role,
        run_id=run_id,
        task_id=cleaned,
        goal=goal,
    )
    return {
        "task": task_store.get_task(cleaned) or leased,
        "run": run,
        "thread_id": thread_id,
    }
