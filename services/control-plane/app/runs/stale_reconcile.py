"""Fail hung role-tagged worker runs so continuous shifts can continue."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import run_store

logger = logging.getLogger(__name__)

# Cursor agent turns time out around 240s; keep headroom for finalize + retries.
DEFAULT_STALE_SECONDS = 720.0
# Lead shifts coordinate specialists and often run longer than a single CLI turn.
DEFAULT_LEAD_STALE_SECONDS = 1800.0
_STALE_SUMMARY = "Continuous worker run exceeded stale timeout"
_PAUSED_ABANDON_SUMMARY = "Paused continuous worker run abandoned after stale timeout"

# Phases that mean a role is still doing (or waiting on) in-flight work.
BUSY_EMPLOYEE_PHASES = frozenset(
    {"queued", "starting", "planning", "executing", "awaiting_approval"}
)
_EARLY_BUSY_PHASES = frozenset({"queued", "starting", "planning"})
# Heartbeat receipts prove the dispatch thread is alive but not that work progressed.
_STALE_IDLE_SKIP_RECEIPT_TYPES = frozenset({"worker_heartbeat"})


def employee_run_stale_seconds() -> float:
    raw = os.environ.get("AXON_WATCH_WORKER_RUN_STALE_SECONDS", "").strip()
    if not raw:
        return DEFAULT_STALE_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_STALE_SECONDS
    return max(60.0, value)


def employee_run_stale_seconds_for_role(role: str | None) -> float:
    """Per-role idle TTL — leads get a longer default for fan-out / board work."""
    base = employee_run_stale_seconds()
    cleaned = str(role or "").strip().lower()
    if cleaned != "lead":
        return base
    raw = os.environ.get("AXON_WATCH_LEAD_RUN_STALE_SECONDS", "").strip()
    if raw:
        try:
            return max(60.0, float(raw))
        except ValueError:
            pass
    return max(base, DEFAULT_LEAD_STALE_SECONDS)


def _parse_iso(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _last_meaningful_transition_timestamp(history_ref: str) -> str | None:
    """Newest history stamp that reflects phase change or non-heartbeat progress."""
    for item in reversed(run_store.list_history(history_ref)):
        from_phase = str(item.get("from_phase") or "").strip()
        to_phase = str(item.get("to_phase") or "").strip()
        if from_phase != to_phase:
            timestamp = str(item.get("timestamp") or "").strip()
            if timestamp:
                return timestamp
            continue
        receipt = item.get("receipt")
        receipt_type = ""
        if isinstance(receipt, dict):
            receipt_type = str(receipt.get("type") or "").strip()
        if receipt_type in _STALE_IDLE_SKIP_RECEIPT_TYPES:
            continue
        timestamp = str(item.get("timestamp") or "").strip()
        if timestamp:
            return timestamp
    return None


def _run_idle_age_seconds(record: dict[str, Any], *, now: datetime) -> float | None:
    """Age since last persisted receipt/transition, ignoring heartbeat-only bumps."""
    history_ref = str(record.get("history_ref") or "").strip()
    stamp = (
        _parse_iso(_last_meaningful_transition_timestamp(history_ref))
        if history_ref
        else None
    )
    if stamp is None:
        stamp = _parse_iso(record.get("started_at"))
    if stamp is None:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return max(0.0, (now - stamp).total_seconds())


def _normalize_cutoff(stale_seconds: float | None, *, role: str | None = None) -> float:
    if stale_seconds is not None:
        return max(60.0, float(stale_seconds))
    return employee_run_stale_seconds_for_role(role)


def _cancel_stale_employee_run_via_pause(
    run_id: str,
    *,
    age: float,
    cutoff: float,
    from_phase: str,
    pause_step: str,
    cancel_step: str,
    receipt_summary: str,
) -> bool:
    from app.runs.service import RunLifecycleError, RunNotFoundError, _transition_record

    record = run_store.get_run(run_id)
    if record is None or str(record.get("phase") or "").strip() != from_phase:
        return False
    try:
        paused = _transition_record(
            record,
            to_phase="paused",
            current_step=pause_step,
            actor="workspace_scheduler",
            receipt_type="stale_worker_cancel",
            receipt_summary=receipt_summary,
        )
        _transition_record(
            paused,
            to_phase="cancelled",
            current_step=cancel_step,
            actor="workspace_scheduler",
            receipt_type="stale_worker_cancel",
            receipt_summary=receipt_summary,
        )
    except (RunLifecycleError, RunNotFoundError):
        logger.exception(
            "stale employee-run cancel skipped for %s phase=%s",
            run_id,
            from_phase,
        )
        return False
    return True


def _cancel_paused_employee_run(run_id: str, *, age: float, cutoff: float) -> bool:
    from app.runs.service import RunLifecycleError, RunNotFoundError, _transition_record

    record = run_store.get_run(run_id)
    if record is None or str(record.get("phase") or "").strip() != "paused":
        return False
    receipt_summary = f"{_PAUSED_ABANDON_SUMMARY} ({int(age)}s > {int(cutoff)}s)"
    try:
        _transition_record(
            record,
            to_phase="cancelled",
            current_step="Paused continuous worker run cancelled after stale timeout",
            actor="workspace_scheduler",
            receipt_type="stale_worker_cancel",
            receipt_summary=receipt_summary,
        )
    except (RunLifecycleError, RunNotFoundError):
        logger.exception("stale paused employee-run cancel skipped for %s", run_id)
        return False
    return True


def _cancel_stale_early_busy_employee_run(
    run_id: str,
    *,
    age: float,
    cutoff: float,
    phase: str,
) -> bool:
    receipt_summary = (
        f"Stale continuous worker run in {phase} cancelled after idle timeout "
        f"({int(age)}s > {int(cutoff)}s)"
    )
    return _cancel_stale_employee_run_via_pause(
        run_id,
        age=age,
        cutoff=cutoff,
        from_phase=phase,
        pause_step=f"Stale continuous worker run paused from {phase}",
        cancel_step="Stale continuous worker run cancelled after idle timeout",
        receipt_summary=receipt_summary,
    )


def reap_stale_employee_runs(
    *,
    now: datetime | None = None,
    stale_seconds: float | None = None,
) -> list[str]:
    """Fail or cancel idle employee-role runs older than the wall-clock TTL.

    Idle age uses the last history receipt/transition so heartbeat-only bumps
    do not mask hung dispatches, while active long turns with real receipts survive.
    Interactive (untagged) runs are left alone. Approval waits are not auto-failed.
    Abandoned paused and early-phase (queued/starting/planning) employee runs are
    cancelled so the role gate can recover without a process restart.
    """
    from app.runs.service import RunLifecycleError, RunNotFoundError, fail_run

    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)

    reaped: list[str] = []
    for record in run_store.list_runs():
        role = str(record.get("employee_role") or "").strip()
        if not role:
            continue
        phase = str(record.get("phase") or "").strip()
        if is_terminal_phase(phase):
            continue
        cutoff = _normalize_cutoff(stale_seconds, role=role)
        age = _run_idle_age_seconds(record, now=moment)
        if age is None or age < cutoff:
            continue
        run_id = str(record.get("run_id") or "").strip()
        if not run_id:
            continue

        if phase == "paused":
            if not _cancel_paused_employee_run(run_id, age=age, cutoff=cutoff):
                continue
            reaped.append(run_id)
            logger.warning(
                "cancelled abandoned paused employee run %s role=%s idle_s=%.0f",
                run_id,
                role,
                age,
            )
            continue

        if phase in _EARLY_BUSY_PHASES:
            if not _cancel_stale_early_busy_employee_run(
                run_id,
                age=age,
                cutoff=cutoff,
                phase=phase,
            ):
                continue
            reaped.append(run_id)
            logger.warning(
                "cancelled stale early-phase employee run %s role=%s phase=%s idle_s=%.0f",
                run_id,
                role,
                phase,
                age,
            )
            continue

        if phase != "executing":
            continue
        try:
            fail_run(
                run_id,
                receipt_summary=f"{_STALE_SUMMARY} ({int(age)}s > {int(cutoff)}s)",
                actor="workspace_scheduler",
            )
        except (RunLifecycleError, RunNotFoundError):
            logger.exception("stale employee-run reap skipped for %s", run_id)
            continue
        reaped.append(run_id)
        logger.warning(
            "reaped stale employee run %s role=%s idle_s=%.0f",
            run_id,
            role,
            age,
        )
    return reaped


__all__ = [
    "BUSY_EMPLOYEE_PHASES",
    "DEFAULT_LEAD_STALE_SECONDS",
    "DEFAULT_STALE_SECONDS",
    "employee_run_stale_seconds",
    "employee_run_stale_seconds_for_role",
    "reap_stale_employee_runs",
]
