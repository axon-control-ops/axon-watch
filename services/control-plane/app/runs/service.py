"""Run lifecycle service for the control-plane thin slice."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.domain.run_state import capability_flags, is_terminal_phase, status_for_phase
from app.domain.run_transitions import can_transition
from app.persistence import run_store

DEFAULT_LANE_ID = "control-plane"


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


def _transition_record(
    record: dict[str, Any],
    *,
    to_phase: str,
    current_step: str | None,
    actor: str,
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
        },
    )

    record = _transition_record(
        record,
        to_phase="starting",
        current_step="Preparing run resources",
        actor="control-plane",
    )
    record = _transition_record(
        record,
        to_phase="executing",
        current_step="Executing thin-slice work",
        actor="control-plane",
    )
    return record


def complete_run(run_id: str) -> dict[str, Any]:
    record = run_store.get_run(run_id)
    if record is None:
        raise RunNotFoundError(f"run not found: {run_id}")

    if record["phase"] != "executing":
        raise RunLifecycleError(
            f"complete requires executing phase, found {record['phase']}",
        )

    return _transition_record(
        record,
        to_phase="completed",
        current_step="Run completed",
        actor="control-plane",
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
