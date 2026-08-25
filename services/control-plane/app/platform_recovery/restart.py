"""Restart recovery: preserve checkpointed work instead of cancelling it."""

from __future__ import annotations

from typing import Any

from app.platform_recovery.autonomy import may_auto_resume_checkpoint
from app.platform_recovery.checkpoints import checkpoint_is_valid, get_checkpoint, write_checkpoint
from app.platform_recovery.store import upsert_recovery_record
from app.runs.restart_reconcile import _EMPLOYEE_RESTART_SUMMARY, _release_restart_interrupted_task


def maybe_preserve_checkpointed_run(record: dict[str, Any]) -> dict[str, Any] | None:
    """Pause a checkpointed employee run so it can resume after restart.

    Returns the paused record when preservation applied, otherwise None so the
    existing cancel-on-restart path can run.
    """
    run_id = str(record.get("run_id") or "").strip()
    if not run_id:
        return None
    if not str(record.get("employee_role") or "").strip():
        return None
    checkpoint = get_checkpoint(run_id)
    if not checkpoint_is_valid(checkpoint):
        return None

    from app.runs.service import RunLifecycleError, RunNotFoundError, _transition_record

    phase = str(record.get("phase") or "").strip()
    if phase not in {"queued", "starting", "planning", "executing", "paused"}:
        return None
    try:
        paused = record
        if phase == "paused":
            paused = record
        elif phase == "executing":
            paused = _transition_record(
                record,
                to_phase="paused",
                current_step="Checkpointed worker paused on control-plane restart",
                actor="control-plane",
                receipt_type="control_plane_restart",
                receipt_summary=(
                    "Checkpoint preserved on control-plane restart; run is RESUMABLE"
                ),
            )
        else:
            paused = _transition_record(
                record,
                to_phase="paused",
                current_step="Checkpointed worker paused on control-plane restart",
                actor="control-plane",
                receipt_type="control_plane_restart",
                receipt_summary=_EMPLOYEE_RESTART_SUMMARY,
            )
    except (RunLifecycleError, RunNotFoundError):
        return None

    write_checkpoint(
        run_id,
        {
            **(checkpoint or {}),
            "recovery_state": "RESUMABLE",
            "current_stage": "paused_after_restart",
        },
    )
    upsert_recovery_record(
        {
            "run_id": run_id,
            "task_id": record.get("task_id"),
            "workspace_id": record.get("workspace_id") or "",
            "bucket": "RESUMABLE",
            "failure_class": "PROCESS_LOST",
            "recovery_state": "RESUMABLE",
            "what_happened": "Control plane restarted while this worker had a valid checkpoint.",
            "why_stale": "control_plane_restart",
            "next_action": (
                "Resume is safe because the checkpoint is valid and the lease was not released."
                if not may_auto_resume_checkpoint()
                else "Autonomy level allows auto-resume of this checkpointed run."
            ),
            "idempotency_key": f"restart:{run_id}",
        }
    )
    return paused


def should_release_lease_on_restart(record: dict[str, Any]) -> bool:
    checkpoint = get_checkpoint(str(record.get("run_id") or ""))
    return not checkpoint_is_valid(checkpoint)


def release_if_uncheckpointed(record: dict[str, Any]) -> None:
    if should_release_lease_on_restart(record):
        _release_restart_interrupted_task(record)


def _preview_item(record: dict[str, Any]) -> dict[str, Any]:
    run_id = str(record.get("run_id") or "")
    checkpoint = get_checkpoint(run_id)
    valid = checkpoint_is_valid(checkpoint)
    return {
        "run_id": run_id,
        "workspace_id": record.get("workspace_id"),
        "employee_role": record.get("employee_role") or "",
        "phase": record.get("phase"),
        "task_id": record.get("task_id"),
        "summary": str(record.get("summary") or "")[:160],
        "checkpoint_valid": valid,
        "updated_at": record.get("updated_at"),
    }


def preview_restart_impact() -> dict[str, Any]:
    """Read-only restart safety check. Does not mutate runs."""
    from app.domain.run_state import is_terminal_phase
    from app.persistence import run_store

    active: list[dict[str, Any]] = []
    resumable: list[dict[str, Any]] = []
    non_resumable: list[dict[str, Any]] = []
    for record in run_store.list_runs():
        phase = str(record.get("phase") or "").strip()
        if is_terminal_phase(phase) or phase == "review_ready":
            continue
        item = _preview_item(record)
        active.append(item)
        role = str(record.get("employee_role") or "").strip()
        if role and item["checkpoint_valid"] and phase in {
            "queued", "starting", "planning", "executing", "paused",
        }:
            resumable.append(item)
        else:
            non_resumable.append(item)

    if non_resumable:
        recommended = (
            "Defer restart, or accept that uncheckpointed in-flight work will be "
            "cancelled and its lease reopened."
        )
        risk = "high" if any(item.get("phase") == "executing" for item in non_resumable) else "medium"
    elif resumable:
        recommended = (
            "Restart is allowed. Checkpointed employee runs stay paused/RESUMABLE; "
            "resume from Recovery Center after boot."
        )
        risk = "low"
    else:
        recommended = "No in-flight runs. Restart now to load current recovery code."
        risk = "low"

    return {
        "active_work": active,
        "resumable_work": resumable,
        "non_resumable_work": non_resumable,
        "recommended_action": recommended,
        "risk": risk,
    }
