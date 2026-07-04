"""Run lifecycle service for the control-plane thin slice."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.domain.run_state import capability_flags, is_terminal_phase, status_for_phase
from app.domain.run_transitions import can_transition
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
) -> dict[str, Any]:
    now = _utc_now_iso()
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    history_ref = f"history/{run_id}"
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
    }
    return _apply_capabilities(record)


def create_run(
    *,
    workspace_id: str,
    mode: str,
    summary: str,
    detail: str = "",
    requires_approval: bool = False,
) -> dict[str, Any]:
    record = _new_run_record(
        workspace_id=workspace_id,
        mode=mode,
        summary=summary,
        detail=detail,
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

    if record["phase"] not in {"executing", "review_ready"}:
        raise RunLifecycleError(
            f"complete requires executing or review_ready phase, found {record['phase']}",
        )

    receipt_summary = (
        "Run completed after operator review"
        if record["phase"] == "review_ready"
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


def list_runs() -> list[dict[str, Any]]:
    return run_store.list_runs()


def list_active_runs() -> list[dict[str, Any]]:
    return [record for record in run_store.list_runs() if not is_terminal_phase(record["phase"])]


def list_pending_approval_runs() -> list[dict[str, Any]]:
    return [record for record in run_store.list_runs() if record["phase"] == "awaiting_approval"]


def list_pending_review_runs() -> list[dict[str, Any]]:
    return [record for record in run_store.list_runs() if record["phase"] == "review_ready"]


def list_pending_approval_records() -> list[dict[str, str]]:
    return [_approval_record_for_run(record) for record in list_pending_approval_runs()]


def approval_summary() -> dict[str, Any]:
    pending_runs = list_pending_approval_runs()
    latest_approval_at = max((record["updated_at"] for record in pending_runs), default=None)
    return {
        "pending_count": len(pending_runs),
        "highest_severity": None,
        "latest_approval_at": latest_approval_at,
    }


def to_runtime_summary_active_run(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": record["run_id"],
        "workspace_id": record["workspace_id"],
        "mode": record["mode"],
        "status": record["status"],
        "phase": record["phase"],
        "title": record["summary"],
        "detail": record["detail"],
        "lane_id": record["lane_id"],
        "updated_at": record["updated_at"],
    }
