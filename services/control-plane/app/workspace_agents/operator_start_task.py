"""Operator-initiated start for a Waiting (open) task ledger row."""

from __future__ import annotations

from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import task_store, worker_scheduler_settings_store
from app.runs.service import (
    RunNotFoundError,
    append_run_execution_receipt,
    create_run,
    get_run,
    list_runs,
)
from app.workspace_agents.lead_fan_out import (
    _deps_completed,
    _employee_for_role,
    _post_assignment_to_employee_thread,
)


class OperatorStartTaskError(ValueError):
    """Domain error for operator Start on the Task Board."""


def _kick_queued_dispatch(run_id: str) -> list[dict[str, Any]]:
    """Promote this specialist run even when continuous workers are paused (Manual)."""
    try:
        from app.workspace_agents.scheduler import kick_lead_fan_out_dispatch

        return kick_lead_fan_out_dispatch(
            starts_bound=1,
            target_run_id=run_id,
        )
    except Exception as exc:  # noqa: BLE001 — convert dispatch internals to operator-safe detail
        raise OperatorStartTaskError(
            f"handoff dispatch failed for {run_id}: {exc}"
        ) from exc


def _safe_get_run(run_id: str) -> dict[str, Any] | None:
    cleaned = str(run_id or "").strip()
    if not cleaned:
        return None
    try:
        return get_run(cleaned)
    except RunNotFoundError:
        return None


def _existing_employee_ide_thread(workspace_id: str, owner_role: str) -> str | None:
    """Resolve the specialist IDE thread without posting another assignment chip."""
    from app.persistence import chat_store

    employee = _employee_for_role(workspace_id, owner_role)
    employee_id = str((employee or {}).get("employee_id") or "").strip()
    if not employee_id:
        return None
    thread = chat_store.find_thread_for_employee(
        workspace_id,
        employee_id=employee_id,
        thread_kind="ide",
    )
    if thread is None:
        return None
    thread_id = str(thread.get("thread_id") or "").strip()
    return thread_id or None


def _dispatch_target_run(run_id: str) -> dict[str, Any]:
    """Dispatch exactly one target run or fail visibly while leaving it retryable."""
    kicked = _kick_queued_dispatch(run_id)
    refreshed = _safe_get_run(run_id)
    phase = str((refreshed or {}).get("phase") or "").strip().lower()
    matched = next(
        (row for row in kicked if str(row.get("run_id") or "").strip() == run_id),
        None,
    )
    if matched is not None:
        return refreshed if phase and phase != "queued" else matched
    if phase and phase != "queued":
        return refreshed or {}
    raise OperatorStartTaskError(
        "handoff remains queued; no worker dispatch slot is available or "
        "worker dispatch is disabled"
    )


def _active_role_run(workspace_id: str, owner_role: str) -> dict[str, Any] | None:
    for run in list_runs():
        if str(run.get("workspace_id") or "").strip() != workspace_id:
            continue
        if str(run.get("employee_role") or "").strip().lower() != owner_role:
            continue
        if not is_terminal_phase(str(run.get("phase") or "").strip()):
            return run
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
        if not run_id:
            raise OperatorStartTaskError(
                "leased handoff is missing its queued run; cancel or repair the task"
            )
        advanced = _dispatch_target_run(run_id)
        thread_id = _existing_employee_ide_thread(workspace_id, owner_role)
        return {
            "task": task_store.get_task(cleaned) or task,
            "run": advanced,
            "thread_id": thread_id,
        }

    if status != "open":
        raise OperatorStartTaskError(
            f"only open/waiting tasks can be started (status={status or 'unknown'})"
        )

    attempts_used = int(task.get("attempts_used") or 0)
    attempt_budget = int(task.get("attempt_budget") or 0)
    if attempt_budget <= 0 or attempts_used >= attempt_budget:
        raise OperatorStartTaskError(
            "task attempt budget is exhausted; cancel it or create a fresh handoff"
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
    if not worker_scheduler_settings_store.is_employee_enabled(
        workspace_id,
        owner_role,
        file_enabled=bool(employee.get("enabled", True)),
    ):
        raise OperatorStartTaskError(
            f'teammate for role "{owner_role}" is paused in Fleet controls'
        )
    busy_run = _active_role_run(workspace_id, owner_role)
    if busy_run is not None:
        raise OperatorStartTaskError(
            f'teammate for role "{owner_role}" already has active run '
            f'{str(busy_run.get("run_id") or "unknown")}'
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
    advanced = _dispatch_target_run(run_id)
    return {
        "task": task_store.get_task(cleaned) or leased,
        "run": advanced,
        "thread_id": thread_id,
    }
