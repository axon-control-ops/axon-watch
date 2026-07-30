"""Operator-initiated start for a Waiting (open) task ledger row."""

from __future__ import annotations

from typing import Any

from app.persistence import task_store
from app.runs.service import (
    RunNotFoundError,
    append_run_execution_receipt,
    create_run,
    get_run,
)
from app.workspace_agents.lead_fan_out import (
    _deps_completed,
    _employee_for_role,
    _post_assignment_to_employee_thread,
)


class OperatorStartTaskError(ValueError):
    """Domain error for operator Start on the Task Board."""


def _kick_queued_dispatch() -> list[dict[str, Any]]:
    """Promote queued specialist runs even when continuous workers are paused (Manual)."""
    try:
        from app.workspace_agents.scheduler import kick_lead_fan_out_dispatch

        return kick_lead_fan_out_dispatch(starts_bound=1)
    except Exception:  # noqa: BLE001 — start still succeeds if kick is momentarily unavailable
        return []


def _safe_get_run(run_id: str) -> dict[str, Any] | None:
    cleaned = str(run_id or "").strip()
    if not cleaned:
        return None
    try:
        return get_run(cleaned)
    except RunNotFoundError:
        return None


def operator_start_task(task_id: str) -> dict[str, Any]:
    """Lease an open task, queue a specialist run, kick dispatch, and post the IDE assignment.

    Manual / Semi pause the continuous scheduler, so Operator Start must kick Lane B
    the same way Lead Send does — otherwise Mission Control shows leased/in-progress
    while the IDE stays QUEUED with nothing running.
    """
    cleaned = str(task_id or "").strip()
    if not cleaned:
        raise OperatorStartTaskError("task_id is required")

    task = task_store.get_task(cleaned)
    if task is None:
        raise OperatorStartTaskError(f"task not found: {cleaned}")

    status = str(task.get("status") or "").strip().lower()
    workspace_id = str(task.get("workspace_id") or "").strip()
    owner_role = str(task.get("owner_role") or "").strip().lower() or "watcher"

    # Already leased + queued (common under Manual): kick dispatch instead of failing.
    if status == "leased":
        if not workspace_id:
            raise OperatorStartTaskError("task is missing workspace_id")
        run_id = str(task.get("run_id") or "").strip()
        run = _safe_get_run(run_id)
        phase = str((run or {}).get("phase") or "").strip().lower()
        if phase and phase not in {"queued", "starting"}:
            raise OperatorStartTaskError(
                f"task is already in progress (phase={phase or 'unknown'})"
            )
        kicked = _kick_queued_dispatch()
        thread_id = None
        if run_id or kicked:
            thread_id = _post_assignment_to_employee_thread(
                workspace_id=workspace_id,
                owner_role=owner_role,
                run_id=run_id or str((kicked[0] if kicked else {}).get("run_id") or ""),
                task_id=cleaned,
                goal=str(task.get("goal") or "").strip(),
            )
        refreshed_run = _safe_get_run(run_id) if run_id else (kicked[0] if kicked else None)
        return {
            "task": task_store.get_task(cleaned) or task,
            "run": refreshed_run or run or {},
            "thread_id": thread_id,
        }

    if status != "open":
        raise OperatorStartTaskError(
            f"only open/waiting tasks can be started (status={status or 'unknown'})"
        )

    if not _deps_completed(task):
        raise OperatorStartTaskError(
            "task is still blocked by unfinished dependencies"
        )

    if not workspace_id:
        raise OperatorStartTaskError("task is missing workspace_id")
    employee = _employee_for_role(workspace_id, owner_role)
    employee_id = str((employee or {}).get("employee_id") or "").strip()
    if not employee_id:
        raise OperatorStartTaskError(
            f'no teammate is staffed for role "{owner_role}"'
        )
    if not bool(employee.get("enabled", True)):
        raise OperatorStartTaskError(
            f'teammate for role "{owner_role}" is disabled'
        )

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
    kicked = _kick_queued_dispatch()
    advanced = next(
        (row for row in kicked if str(row.get("run_id") or "") == run_id),
        None,
    )
    return {
        "task": task_store.get_task(cleaned) or leased,
        "run": advanced or _safe_get_run(run_id) or run,
        "thread_id": thread_id,
    }
