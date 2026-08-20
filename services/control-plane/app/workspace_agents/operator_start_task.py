"""Operator-initiated start for a Waiting (open) task ledger row."""

from __future__ import annotations

import logging
import time
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

logger = logging.getLogger(__name__)

DISPATCH_RECEIPT_WAIT_SECONDS = 25.0
DISPATCH_RECEIPT_POLL_INTERVAL = 0.25


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


def _run_has_receipt_type(run_id: str, receipt_type: str) -> bool:
    record = _safe_get_run(run_id)
    if record is None:
        return False
    history_ref = str(record.get("history_ref") or "").strip()
    if not history_ref:
        return False
    from app.persistence import run_store

    want = receipt_type.strip()
    for item in run_store.list_history(history_ref):
        receipt = item.get("receipt")
        if isinstance(receipt, dict) and str(receipt.get("type") or "").strip() == want:
            return True
    return False


def _wait_for_worker_dispatch_started(
    run_id: str,
    *,
    timeout: float = DISPATCH_RECEIPT_WAIT_SECONDS,
) -> bool:
    """Block until the background worker thread records dispatch, or timeout."""
    deadline = time.monotonic() + max(1.0, float(timeout))
    while time.monotonic() < deadline:
        if _run_has_receipt_type(run_id, "worker_dispatch_started"):
            return True
        refreshed = _safe_get_run(run_id)
        phase = str((refreshed or {}).get("phase") or "").strip().lower()
        if phase in {"failed", "cancelled", "completed"}:
            return False
        time.sleep(DISPATCH_RECEIPT_POLL_INTERVAL)
    return _run_has_receipt_type(run_id, "worker_dispatch_started")


def _recover_undispatched_operator_start(run_id: str) -> None:
    """Terminate an undispatched run and reopen its leased task for retry."""
    from app.runs.service import RunLifecycleError, RunNotFoundError, fail_run, stop_run

    try:
        record = _safe_get_run(run_id) or {}
        phase = str(record.get("phase") or "").strip().lower()
        if phase in {"queued", "starting", "planning", "waiting_external"}:
            paused = stop_run(run_id)
            if str(paused.get("phase") or "").strip().lower() == "paused":
                stop_run(run_id)
        else:
            fail_run(
                run_id,
                receipt_summary=(
                    "Operator start did not receive worker_dispatch_started within "
                    f"{int(DISPATCH_RECEIPT_WAIT_SECONDS)}s; task reopened for retry"
                ),
                actor="operator",
            )
    except (RunLifecycleError, RunNotFoundError):
        logger.exception("could not terminate undispatched operator start run %s", run_id)
    task_store.reopen_orphaned_leased_tasks(
        terminal_run_ids=[run_id],
        terminal_outcome="operator start dispatch timeout; retry Run verification",
        refund_attempts=True,
    )


def _finalize_operator_dispatch(run_id: str, advanced: dict[str, Any]) -> dict[str, Any]:
    """Ensure worker dispatch actually started before returning success to the UI."""
    phase = str((advanced or {}).get("phase") or "").strip().lower()
    refreshed = _safe_get_run(run_id)
    live_phase = str((refreshed or {}).get("phase") or "").strip().lower()
    busy_phase = phase if phase in {"executing", "starting", "planning"} else live_phase
    if busy_phase not in {"executing", "starting", "planning"}:
        return advanced if advanced else (refreshed or {})
    if _wait_for_worker_dispatch_started(run_id):
        refreshed = _safe_get_run(run_id)
        live_phase = str((refreshed or {}).get("phase") or "").strip().lower()
        if live_phase in {"executing", "starting", "planning"}:
            return refreshed or advanced
        return advanced
    _recover_undispatched_operator_start(run_id)
    raise OperatorStartTaskError(
        "handoff dispatch did not start within timeout; task reopened — "
        "use Run verification again"
    )


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
        candidate = refreshed if phase and phase != "queued" else matched
        return _finalize_operator_dispatch(run_id, candidate)
    if phase and phase != "queued":
        return _finalize_operator_dispatch(run_id, refreshed or {})
    raise OperatorStartTaskError(
        "handoff remains queued; no worker dispatch slot is available or "
        "worker dispatch is disabled"
    )


def _find_run_for_stale_task_id(task_id: str) -> dict[str, Any] | None:
    """Best-effort run lookup when the UI still references a vanished task row."""
    cleaned = str(task_id or "").strip()
    if not cleaned:
        return None
    matches = [
        run
        for run in list_runs()
        if str(run.get("task_id") or "").strip() == cleaned
    ]
    if not matches:
        return None
    matches.sort(
        key=lambda row: str(row.get("updated_at") or row.get("started_at") or ""),
        reverse=True,
    )
    return matches[0]


def _repair_missing_verification_task(task_id: str) -> dict[str, Any] | None:
    """Bind operator Start to an open verification ticket when a stale task id 404s."""
    from app.workspace_agents.lead_verification_handoff import (
        enqueue_specialist_verification_task,
        find_open_verification_task,
        is_verification_task,
        resolve_verification_baseline,
        source_run_from_verification_goal,
    )

    run = _find_run_for_stale_task_id(task_id)
    if run is None:
        return None
    workspace_id = str(run.get("workspace_id") or "").strip()
    owner_role = str(run.get("employee_role") or "").strip().lower()
    run_id = str(run.get("run_id") or "").strip()
    if not workspace_id or not owner_role or not run_id:
        return None

    existing = find_open_verification_task(workspace_id, owner_role)
    if existing is not None:
        return existing

    for status in ("open", "leased"):
        for row in task_store.list_tasks(workspace_id=workspace_id, status=status, limit=100):
            if str(row.get("owner_role") or "").strip().lower() != owner_role:
                continue
            if is_verification_task(row):
                return row

    employee = _employee_for_role(workspace_id, owner_role)
    implementation_run = run_id
    bound_task = task_store.get_task(str(run.get("task_id") or "").strip()) if run.get("task_id") else None
    if bound_task and is_verification_task(bound_task):
        parent = source_run_from_verification_goal(str(bound_task.get("goal") or ""))
        if parent and parent != run_id:
            implementation_run = parent
        else:
            baseline_commit, baseline_ref = resolve_verification_baseline(
                workspace_id=workspace_id,
                task=bound_task,
            )
            if baseline_ref and baseline_ref.startswith("worker/"):
                implementation_run = baseline_ref.removeprefix("worker/")
            elif baseline_commit:
                implementation_run = run_id
    return enqueue_specialist_verification_task(
        workspace_id=workspace_id,
        employee_name=str((employee or {}).get("name") or owner_role),
        employee_role=owner_role,
        run_id=implementation_run,
        blockers=str(run.get("detail") or ""),
    )


def _resolve_task_for_operator_start(task_id: str) -> dict[str, Any]:
    cleaned = str(task_id or "").strip()
    if not cleaned:
        raise OperatorStartTaskError("task_id is required")
    task = task_store.get_task(cleaned)
    if task is not None:
        return task
    repaired = _repair_missing_verification_task(cleaned)
    if repaired is None:
        raise OperatorStartTaskError(f"task not found: {cleaned}")
    return repaired


def _maybe_reopen_terminal_leased_task(task: dict[str, Any]) -> dict[str, Any]:
    """Reopen leased tickets whose bound run already failed so Run verification can retry."""
    status = str(task.get("status") or "").strip().lower()
    if status != "leased":
        return task
    run_id = str(task.get("run_id") or "").strip()
    if not run_id:
        return task
    run = _safe_get_run(run_id)
    phase = str((run or {}).get("phase") or "").strip().lower()
    if not phase or not is_terminal_phase(phase):
        return task
    task_id = str(task.get("task_id") or "").strip()
    if not task_id:
        return task
    try:
        return task_store.fail_task(
            task_id,
            run_id=run_id,
            terminal_outcome=f"operator retry after {phase} run",
            reopen_if_budget_remaining=True,
        )
    except task_store.TaskLedgerError as exc:
        raise OperatorStartTaskError(str(exc)) from exc


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

    task = _maybe_reopen_terminal_leased_task(_resolve_task_for_operator_start(cleaned))
    cleaned = str(task.get("task_id") or cleaned).strip()

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
        from app.workspace_agents.task_dependencies import dependency_blocker_message

        detail = dependency_blocker_message(task) or "task is still blocked by unfinished dependencies"
        raise OperatorStartTaskError(detail)

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
