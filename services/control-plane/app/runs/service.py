"""Run lifecycle service for the control-plane thin slice."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.domain.run_state import capability_flags, is_terminal_phase, status_for_phase
from app.domain.run_transitions import can_transition
from app.chat.command_intent import humanize_run_summary, is_auto_complete_run_summary
from app.persistence import run_store

DEFAULT_LANE_ID = "control-plane"
_PAUSE_ON_STOP_PHASES = {"queued", "starting", "planning", "executing", "waiting_external"}
_CANCEL_ON_STOP_PHASES = {"awaiting_input", "awaiting_approval", "paused"}
_RESUME_TARGETS = {
    "paused": ("executing", "Run resumed by operator"),
    "awaiting_input": ("planning", "Run resumed after operator input"),
    "review_ready": ("executing", "Run resumed for follow-up work"),
}


class RunLifecycleError(ValueError):
    pass


class RunNotFoundError(RunLifecycleError):
    pass


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _apply_capabilities(record: dict[str, Any]) -> dict[str, Any]:
    record.update(capability_flags(record["phase"]))
    record["status"] = status_for_phase(record["phase"])
    return record


def _approval_record_for_run(record: dict[str, Any]) -> dict[str, str]:
    return {
        "approval_id": f"approval_{record['run_id']}",
        "run_id": record["run_id"],
        "workspace_id": record["workspace_id"],
    }


def _transition_record(
    record: dict[str, Any],
    *,
    to_phase: str,
    current_step: str | None,
    actor: str,
    receipt_type: str = "phase_transition",
    receipt_summary: str | None = None,
) -> dict[str, Any]:
    from_phase = record["phase"]
    if not can_transition(from_phase, to_phase):
        raise RunLifecycleError(f"transition not allowed: {from_phase} -> {to_phase}")

    now = _utc_now_iso()
    record["phase"] = to_phase
    record["updated_at"] = now
    if current_step is not None:
        record["current_step"] = current_step
    if is_terminal_phase(to_phase):
        record["ended_at"] = now

    _apply_capabilities(record)
    run_store.append_transition(
        record["history_ref"],
        {
            "from_phase": from_phase,
            "to_phase": to_phase,
            "timestamp": now,
            "actor": actor,
            "current_step": record.get("current_step"),
            "receipt": {
                "type": receipt_type,
                "summary": receipt_summary or f"{from_phase} -> {to_phase}",
            },
        },
    )
    return run_store.save_run(record)


def _new_run_record(
    *,
    workspace_id: str,
    mode: str,
    summary: str,
    detail: str,
    employee_role: str | None = None,
) -> dict[str, Any]:
    now = _utc_now_iso()
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    history_ref = f"history/{run_id}"
    cleaned_role = str(employee_role or "").strip() or None
    record = {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "lane_id": DEFAULT_LANE_ID,
        "mode": mode,
        "phase": "queued",
        "summary": summary,
        "detail": detail,
        "started_at": now,
        "updated_at": now,
        "ended_at": None,
        "current_step": "Run queued",
        "history_ref": history_ref,
        "employee_role": cleaned_role,
    }
    return _apply_capabilities(record)


def create_run(
    *,
    workspace_id: str,
    mode: str,
    summary: str,
    detail: str = "",
    requires_approval: bool = False,
    employee_role: str | None = None,
) -> dict[str, Any]:
    record = _new_run_record(
        workspace_id=workspace_id,
        mode=mode,
        summary=summary,
        detail=detail,
        employee_role=employee_role,
    )
    run_store.save_run(record)
    run_store.append_transition(
        record["history_ref"],
        {
            "from_phase": None,
            "to_phase": "queued",
            "timestamp": record["started_at"],
            "actor": "control-plane",
            "current_step": record["current_step"],
            "receipt": {
                "type": "run_created",
                "summary": "Run created",
            },
        },
    )

    record = _transition_record(
        record,
        to_phase="starting",
        current_step="Preparing run resources",
        actor="control-plane",
        receipt_type="system_transition",
        receipt_summary="Run accepted and starting",
    )
    if requires_approval:
        record = _transition_record(
            record,
            to_phase="planning",
            current_step="Preparing approval boundary",
            actor="control-plane",
            receipt_type="system_transition",
            receipt_summary="Run entered planning before approval",
        )
        return _transition_record(
            record,
            to_phase="awaiting_approval",
            current_step="Awaiting operator approval",
            actor="control-plane",
            receipt_type="approval_requested",
            receipt_summary="Run requires operator approval before execution",
        )

    record = _transition_record(
        record,
        to_phase="executing",
        current_step="Executing thin-slice work",
        actor="control-plane",
        receipt_type="system_transition",
        receipt_summary="Run entered execution",
    )
    return record


def complete_run(run_id: str) -> dict[str, Any]:
    record = run_store.get_run(run_id)
    if record is None:
        raise RunNotFoundError(f"run not found: {run_id}")

    if record["phase"] not in {"executing", "review_ready", "paused"}:
        raise RunLifecycleError(
            f"complete requires executing, review_ready, or paused phase, found {record['phase']}",
        )

    receipt_summary = (
        "Run completed after operator review"
        if record["phase"] == "review_ready"
        else "Run completed by operator"
        if record["phase"] == "paused"
        else "Run completed"
    )
    return _transition_record(
        record,
        to_phase="completed",
        current_step="Run completed",
        actor="control-plane",
        receipt_type="operator_complete",
        receipt_summary=receipt_summary,
    )


def fail_run(
    run_id: str,
    *,
    receipt_summary: str = "Run failed",
    actor: str = "control-plane",
) -> dict[str, Any]:
    record = run_store.get_run(run_id)
    if record is None:
        raise RunNotFoundError(f"run not found: {run_id}")

    if record["phase"] not in {"executing", "review_ready", "paused"}:
        raise RunLifecycleError(
            f"fail requires executing, review_ready, or paused phase, found {record['phase']}",
        )

    # Keep operator-visible current_step informative — never bare "Run failed".
    step = " ".join(str(receipt_summary or "").split()).strip() or "Run failed"
    if len(step) > 180:
        step = step[:179].rstrip() + "…"

    return _transition_record(
        record,
        to_phase="failed",
        current_step=step,
        actor=actor,
        receipt_type="run_failed",
        receipt_summary=receipt_summary,
    )


def mark_review_ready(run_id: str) -> dict[str, Any]:
    record = run_store.get_run(run_id)
    if record is None:
        raise RunNotFoundError(f"run not found: {run_id}")

    if record["phase"] != "executing":
        raise RunLifecycleError(
            f"review_ready requires executing phase, found {record['phase']}",
        )

    return _transition_record(
        record,
        to_phase="review_ready",
        current_step="Awaiting operator review",
        actor="control-plane",
        receipt_type="review_ready",
        receipt_summary="Active execution stopped; run awaiting operator review",
    )


def stop_run(run_id: str) -> dict[str, Any]:
    from app.cli_runtime.process_registry import terminate

    terminate(run_id)
    record = run_store.get_run(run_id)
    if record is None:
        raise RunNotFoundError(f"run not found: {run_id}")

    phase = record["phase"]
    if phase in _PAUSE_ON_STOP_PHASES:
        return _transition_record(
            record,
            to_phase="paused",
            current_step="Run paused by operator stop",
            actor="operator",
            receipt_type="operator_stop",
            receipt_summary="Operator stopped the run; execution paused",
        )

    if phase in _CANCEL_ON_STOP_PHASES:
        return _transition_record(
            record,
            to_phase="cancelled",
            current_step="Run cancelled by operator stop",
            actor="operator",
            receipt_type="operator_stop",
            receipt_summary="Operator stopped the run; execution cancelled",
        )

    raise RunLifecycleError(f"stop requires stoppable phase, found {phase}")


def resume_run(run_id: str) -> dict[str, Any]:
    record = run_store.get_run(run_id)
    if record is None:
        raise RunNotFoundError(f"run not found: {run_id}")

    phase = record["phase"]
    # One-shot read-only commands must complete, not resume into a zombie executing phase.
    if phase == "review_ready" and is_auto_complete_run_summary(str(record.get("summary") or "")):
        return _transition_record(
            record,
            to_phase="completed",
            current_step="Run completed",
            actor="control-plane",
            receipt_type="operator_complete",
            receipt_summary=(
                "One-shot command does not need resume; marked completed from review_ready"
            ),
        )

    transition = _RESUME_TARGETS.get(phase)
    if transition is None:
        raise RunLifecycleError(f"resume requires resumable phase, found {phase}")

    to_phase, current_step = transition
    return _transition_record(
        record,
        to_phase=to_phase,
        current_step=current_step,
        actor="operator",
        receipt_type="operator_resume",
        receipt_summary=f"Operator resumed the run from {phase}",
    )


def approve_run(run_id: str) -> dict[str, Any]:
    record = run_store.get_run(run_id)
    if record is None:
        raise RunNotFoundError(f"run not found: {run_id}")

    if record["phase"] != "awaiting_approval":
        raise RunLifecycleError(
            f"approve requires awaiting_approval phase, found {record['phase']}",
        )

    return _transition_record(
        record,
        to_phase="executing",
        current_step="Run approved by operator",
        actor="operator",
        receipt_type="operator_approve",
        receipt_summary="Operator approved the run to continue execution",
    )


def reject_run(run_id: str) -> dict[str, Any]:
    record = run_store.get_run(run_id)
    if record is None:
        raise RunNotFoundError(f"run not found: {run_id}")

    if record["phase"] != "awaiting_approval":
        raise RunLifecycleError(
            f"reject requires awaiting_approval phase, found {record['phase']}",
        )

    return _transition_record(
        record,
        to_phase="cancelled",
        current_step="Run rejected by operator",
        actor="operator",
        receipt_type="operator_reject",
        receipt_summary="Operator rejected the run at the approval boundary",
    )


def get_run(run_id: str) -> dict[str, Any]:
    record = run_store.get_run(run_id)
    if record is None:
        raise RunNotFoundError(f"run not found: {run_id}")
    return record


def get_run_history(run_id: str) -> dict[str, Any]:
    record = get_run(run_id)
    items = run_store.list_history(record["history_ref"])
    return {
        "run_id": record["run_id"],
        "history_ref": record["history_ref"],
        "items": items,
        "count": len(items),
    }


def touch_run_activity(run_id: str) -> dict[str, Any] | None:
    """Refresh updated_at for in-flight runs (UI/API freshness only; stale reap uses history)."""
    record = run_store.get_run(run_id)
    if record is None:
        return None
    if is_terminal_phase(str(record.get("phase") or "")):
        return None
    record["updated_at"] = _utc_now_iso()
    return run_store.save_run(record)


def append_run_execution_receipt(
    run_id: str,
    *,
    receipt_type: str,
    receipt_summary: str,
    actor: str = "command_executor",
    success: bool = True,
    intent: str | None = None,
) -> dict[str, Any]:
    record = get_run(run_id)
    now = _utc_now_iso()
    phase = record["phase"]
    summary = receipt_summary
    if intent:
        summary = f"{receipt_summary} · intent={intent} · success={success}"

    run_store.append_transition(
        record["history_ref"],
        {
            "from_phase": phase,
            "to_phase": phase,
            "timestamp": now,
            "actor": actor,
            "current_step": record.get("current_step"),
            "receipt": {
                "type": receipt_type,
                "summary": summary,
            },
        },
    )
    record["updated_at"] = now
    return run_store.save_run(record)



from app.runs.queries import (
    approval_summary,
    is_background_employee_run,
    list_active_runs,
    list_operator_facing_runs,
    list_operator_facing_active_runs,
    list_pending_approval_records,
    list_pending_approval_runs,
    list_pending_review_runs,
    list_runs,
    to_runtime_summary_active_run,
)
from app.runs.restart_reconcile import reconcile_orphaned_runs_on_startup
from app.runs.employee_retention import (
    DEFAULT_KEEP_PER_ROLE,
    drain_terminal_employee_runs,
    employee_run_retention_per_role,
    prune_terminal_employee_runs,
)
from app.runs.review_ready_reconcile import (
    DEFAULT_REVIEW_READY_STALE_SECONDS,
    reap_abandoned_review_ready_runs,
    review_ready_stale_seconds,
)
from app.runs.stale_reconcile import (
    BUSY_EMPLOYEE_PHASES,
    DEFAULT_STALE_SECONDS,
    employee_run_stale_seconds,
    reap_stale_employee_runs,
)
