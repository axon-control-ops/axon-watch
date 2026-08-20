"""Restart-time reconciliation for orphaned control-plane runs."""

from __future__ import annotations

from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import run_store

_RESTART_INTERRUPT_SUMMARY = "Run interrupted by control-plane restart"
_EMPLOYEE_RESTART_SUMMARY = "Continuous worker dispatch lost on control-plane restart"
_EMPLOYEE_MISSING_TASK_SUMMARY = "Continuous worker dispatch cancelled: linked task is missing"


def _release_restart_interrupted_task(record: dict[str, Any]) -> None:
    """Return the exact cancelled worker lease without charging an attempt."""
    run_id = str(record.get("run_id") or "").strip()
    if not run_id:
        return
    from app.persistence import task_store

    task_store.reopen_orphaned_leased_tasks(
        terminal_run_ids=[run_id],
        terminal_outcome="control-plane restart; lease released without consuming an attempt",
        refund_attempts=True,
    )


def _cancel_employee_run_on_restart(record: dict[str, Any]) -> dict[str, Any] | None:
    """Cancel role-tagged worker runs so the scheduler can restart shifts cleanly."""
    from app.runs.service import RunLifecycleError, RunNotFoundError, _transition_record

    phase = str(record.get("phase") or "").strip()
    if is_terminal_phase(phase) or phase == "review_ready":
        return None

    run_id = str(record.get("run_id") or "").strip()
    if not run_id:
        return None

    try:
        if phase == "executing":
            paused = _transition_record(
                record,
                to_phase="paused",
                current_step="Continuous worker dispatch paused on control-plane restart",
                actor="control-plane",
                receipt_type="control_plane_restart",
                receipt_summary=_EMPLOYEE_RESTART_SUMMARY,
            )
            cancelled = _transition_record(
                paused,
                to_phase="cancelled",
                current_step="Continuous worker dispatch cancelled after control-plane restart",
                actor="control-plane",
                receipt_type="control_plane_restart",
                receipt_summary=_EMPLOYEE_RESTART_SUMMARY,
            )
            _release_restart_interrupted_task(record)
            return cancelled

        if phase in {"awaiting_approval", "awaiting_input", "waiting_external", "paused"}:
            cancelled = _transition_record(
                record,
                to_phase="cancelled",
                current_step="Continuous worker dispatch cancelled after control-plane restart",
                actor="control-plane",
                receipt_type="control_plane_restart",
                receipt_summary=_EMPLOYEE_RESTART_SUMMARY,
            )
            _release_restart_interrupted_task(record)
            return cancelled

        if phase in {"queued", "starting", "planning"}:
            paused = _transition_record(
                record,
                to_phase="paused",
                current_step="Continuous worker dispatch paused on control-plane restart",
                actor="control-plane",
                receipt_type="control_plane_restart",
                receipt_summary=_EMPLOYEE_RESTART_SUMMARY,
            )
            cancelled = _transition_record(
                paused,
                to_phase="cancelled",
                current_step="Continuous worker dispatch cancelled after control-plane restart",
                actor="control-plane",
                receipt_type="control_plane_restart",
                receipt_summary=_EMPLOYEE_RESTART_SUMMARY,
            )
            _release_restart_interrupted_task(record)
            return cancelled
    except (RunLifecycleError, RunNotFoundError):
        return None

    return None


def interrupt_run_on_restart(run_id: str) -> dict[str, Any] | None:
    """Mark a non-terminal run stopped after the control-plane process restarted."""
    from app.runs.service import _transition_record, fail_run

    record = run_store.get_run(run_id)
    if record is None:
        return None

    if str(record.get("employee_role") or "").strip():
        return _cancel_employee_run_on_restart(record)

    phase = record["phase"]
    if is_terminal_phase(phase) or phase == "review_ready":
        return None

    if phase == "executing":
        return fail_run(
            run_id,
            receipt_summary=_RESTART_INTERRUPT_SUMMARY,
            actor="control-plane",
        )

    if phase in {"awaiting_approval", "awaiting_input", "waiting_external", "paused"}:
        return _transition_record(
            record,
            to_phase="cancelled",
            current_step="Run cancelled after control-plane restart",
            actor="control-plane",
            receipt_type="control_plane_restart",
            receipt_summary=_RESTART_INTERRUPT_SUMMARY,
        )

    if phase in {"queued", "starting", "planning"}:
        paused = _transition_record(
            record,
            to_phase="paused",
            current_step="Run paused after control-plane restart",
            actor="control-plane",
            receipt_type="control_plane_restart",
            receipt_summary=_RESTART_INTERRUPT_SUMMARY,
        )
        return _transition_record(
            paused,
            to_phase="cancelled",
            current_step="Run cancelled after control-plane restart",
            actor="control-plane",
            receipt_type="control_plane_restart",
            receipt_summary=_RESTART_INTERRUPT_SUMMARY,
        )

    return None


def reconcile_orphaned_runs_on_startup(*, boot_id: str) -> list[str]:
    """Fail or cancel in-flight runs left behind by a prior control-plane process."""
    reconciled: list[str] = []
    for record in run_store.list_runs():
        if interrupt_run_on_restart(record["run_id"]) is not None:
            reconciled.append(record["run_id"])

    return reconciled


def reconcile_employee_runs_missing_tasks() -> list[str]:
    """Cancel active employee runs whose durable task row disappeared."""
    from app.persistence import task_store
    from app.runs.service import RunLifecycleError, RunNotFoundError, _transition_record

    reconciled: list[str] = []
    for record in run_store.list_runs():
        if is_terminal_phase(str(record.get("phase") or "")):
            continue
        if not str(record.get("employee_role") or "").strip():
            continue
        task_id = str(record.get("task_id") or "").strip()
        if not task_id or task_store.get_task(task_id) is not None:
            continue
        try:
            phase = str(record.get("phase") or "").strip()
            candidate = record
            if phase == "executing":
                candidate = _transition_record(
                    record,
                    to_phase="paused",
                    current_step="Continuous worker dispatch paused: linked task is missing",
                    actor="control-plane",
                    receipt_type="task_ledger_reconcile",
                    receipt_summary=f"{_EMPLOYEE_MISSING_TASK_SUMMARY} (task_id={task_id})",
                )
            _transition_record(
                candidate,
                to_phase="cancelled",
                current_step=_EMPLOYEE_MISSING_TASK_SUMMARY,
                actor="control-plane",
                receipt_type="task_ledger_reconcile",
                receipt_summary=f"{_EMPLOYEE_MISSING_TASK_SUMMARY} (task_id={task_id})",
            )
        except (RunLifecycleError, RunNotFoundError):
            continue
        reconciled.append(str(record.get("run_id") or ""))
    return reconciled


__all__ = [
    "interrupt_run_on_restart",
    "reconcile_employee_runs_missing_tasks",
    "reconcile_orphaned_runs_on_startup",
]
