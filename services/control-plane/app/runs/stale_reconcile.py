"""Fail hung role-tagged worker runs so continuous shifts can continue."""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import run_store

logger = logging.getLogger(__name__)

# Sized for Cursor, whose agent turns time out around 240s. Claude/Codex shifts
# routinely run longer, and three worker runs were stale-failed at 752-766s while
# still doing real work — the reaper was killing progress, not hangs. 1200s keeps
# genuine hang detection well inside the 1800s lead cutoff.
# Override per host with AXON_WATCH_WORKER_RUN_STALE_SECONDS.
DEFAULT_STALE_SECONDS = 1200.0
# Lead shifts coordinate specialists and often run longer than a single CLI turn.
DEFAULT_LEAD_STALE_SECONDS = 1800.0
# Canary/production OTA (expo export + eas update) regularly exceeds 30 minutes when
# Dana blocks on Cursor shellToolCall — do not stale-fail Mid-export.
DEFAULT_OTA_LEAD_STALE_SECONDS = 5400.0
# Full-suite npm/jest verification shifts routinely exceed the default 1200s worker TTL.
DEFAULT_VERIFICATION_STALE_SECONDS = 3600.0
_STALE_SUMMARY = "Continuous worker run exceeded stale timeout"
_PAUSED_ABANDON_SUMMARY = "Paused continuous worker run abandoned after stale timeout"
_OTA_RUN_TEXT_RE = re.compile(
    r"(?i)\b(?:ota(?:\s*canary|\s*production)?|canary\s*ota|eas\s+update|expo\s+export)\b"
)
_HOST_SHIP_CMDLINE_RE = re.compile(
    r"(?i)(?:npm\s+run\s+ota(?::[\w-]*)?|ota:(?:canary|production)|"
    r"eas(?:-wrapper)?\s+update|expo\s+export)"
)
_HOST_VERIFY_CMDLINE_RE = re.compile(r"(?i)(?:\bjest\b|npm\s+test\b|\bvitest\b)")

# Phases that mean a role is still doing (or waiting on) in-flight work.
BUSY_EMPLOYEE_PHASES = frozenset(
    {"queued", "starting", "planning", "executing", "awaiting_approval"}
)
_EARLY_BUSY_PHASES = frozenset({"queued", "starting", "planning"})
# Heartbeat receipts prove the dispatch thread is alive but not that work progressed.
_STALE_IDLE_SKIP_RECEIPT_TYPES = frozenset({"worker_heartbeat"})
# Executing runs without worker_dispatch_started are operator-visible zombies.
DEFAULT_UNDISPATCHED_WORKER_SECONDS = 90.0
# Executing runs that recorded worker_dispatch_started but never reached isolation
# or any other progress receipt — dispatch thread died or hung after claiming.
DEFAULT_GHOST_DISPATCH_SECONDS = 90.0
_GHOST_DISPATCH_PROGRESS_RECEIPT_TYPES = frozenset(
    {
        "worker_isolation_created",
        "worker_heartbeat",
        "worker_progress",
        "worker_delivery",
        "verification_terminal_enqueued",
        "verification_terminal_unrunnable",
        "worker_delivery_verification_receipt",
        "auto_ask_resolution",
        "worker_ask_block",
        "runtime_dispatch",
    }
)
# Receipts that mean Lane B or verify-enqueue progressed after isolation was recorded.
_POST_ISOLATION_LANE_B_RECEIPT_TYPES = frozenset(
    {
        "agent_sandbox_started",
        "agent_sandbox_skipped",
        "runtime_dispatch",
        "worker_progress",
        "verification_terminal_enqueued",
        "verification_terminal_unrunnable",
        "verification_terminal_enqueue_failed",
    }
)


def undispatched_worker_seconds() -> float:
    raw = os.environ.get("AXON_WATCH_UNDISPATCHED_WORKER_SECONDS", "").strip()
    if not raw:
        return DEFAULT_UNDISPATCHED_WORKER_SECONDS
    try:
        return max(30.0, float(raw))
    except ValueError:
        return DEFAULT_UNDISPATCHED_WORKER_SECONDS


def ghost_dispatch_seconds() -> float:
    raw = os.environ.get("AXON_WATCH_GHOST_DISPATCH_SECONDS", "").strip()
    if not raw:
        return DEFAULT_GHOST_DISPATCH_SECONDS
    try:
        return max(30.0, float(raw))
    except ValueError:
        return DEFAULT_GHOST_DISPATCH_SECONDS


def _run_has_any_receipt_type(record: dict[str, Any], receipt_types: frozenset[str]) -> bool:
    history_ref = str(record.get("history_ref") or "").strip()
    if not history_ref:
        return False
    for item in run_store.list_history(history_ref):
        receipt = item.get("receipt")
        if not isinstance(receipt, dict):
            continue
        if str(receipt.get("type") or "").strip() in receipt_types:
            return True
    return False


def run_has_dispatch_progress(record: dict[str, Any]) -> bool:
    return _run_has_any_receipt_type(record, _GHOST_DISPATCH_PROGRESS_RECEIPT_TYPES)


def run_has_post_isolation_lane_b_stall(
    record: dict[str, Any],
    *,
    now: datetime | None = None,
) -> bool:
    """True when isolation was recorded but Lane B / verify enqueue never started."""
    phase = str(record.get("phase") or "").strip()
    if phase not in {"executing", "starting", "planning"}:
        return False
    if not str(record.get("task_id") or "").strip():
        return False
    if not _run_has_receipt_type(record, "worker_isolation_created"):
        return False
    if _run_has_any_receipt_type(record, _POST_ISOLATION_LANE_B_RECEIPT_TYPES):
        return False
    age = _isolation_created_age_seconds(record, now=now or datetime.now(timezone.utc))
    if age is None:
        return False
    return age >= ghost_dispatch_seconds()


def _isolation_created_age_seconds(
    record: dict[str, Any],
    *,
    now: datetime,
) -> float | None:
    history_ref = str(record.get("history_ref") or "").strip()
    if not history_ref:
        return None
    for item in run_store.list_history(history_ref):
        receipt = item.get("receipt")
        if not isinstance(receipt, dict):
            continue
        if str(receipt.get("type") or "").strip() != "worker_isolation_created":
            continue
        stamp = _parse_iso(item.get("timestamp"))
        if stamp is None:
            stamp = _parse_iso(record.get("updated_at"))
        if stamp is None:
            return None
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return max(0.0, (now - stamp).total_seconds())
    return None


def run_has_ghost_dispatch(record: dict[str, Any], *, now: datetime | None = None) -> bool:
    """True when dispatch claimed a run but never produced isolation/progress."""
    phase = str(record.get("phase") or "").strip()
    if phase not in {"executing", "starting", "planning"}:
        return False
    if not str(record.get("task_id") or "").strip():
        return False
    if not _run_has_receipt_type(record, "worker_dispatch_started"):
        return False
    if _run_has_any_receipt_type(record, _GHOST_DISPATCH_PROGRESS_RECEIPT_TYPES):
        return False
    age = _run_idle_age_seconds(record, now=now or datetime.now(timezone.utc))
    if age is None:
        return False
    return age >= ghost_dispatch_seconds()


def recover_ghost_dispatch_run(
    run_id: str,
    *,
    actor: str = "workspace_scheduler",
    receipt_summary: str | None = None,
) -> bool:
    """Release the in-memory dispatch claim, fail the run, and reopen its leased task."""
    from app.persistence import task_store
    from app.runs.service import RunLifecycleError, RunNotFoundError, fail_run
    from app.workspace_agents.worker_dispatch_support import release_worker_dispatch

    cleaned = str(run_id or "").strip()
    if not cleaned:
        return False
    record = run_store.get_run(cleaned)
    if record is None or not run_has_ghost_dispatch(record):
        return False
    release_worker_dispatch(cleaned)
    summary = receipt_summary or (
        "Continuous worker dispatch never reached isolation/progress after "
        f"worker_dispatch_started (>{int(ghost_dispatch_seconds())}s); task reopened"
    )
    try:
        fail_run(cleaned, receipt_summary=summary, actor=actor)
    except (RunLifecycleError, RunNotFoundError):
        logger.exception("ghost dispatch recover failed for %s", cleaned)
        return False
    task_store.reopen_orphaned_leased_tasks(
        terminal_run_ids=[cleaned],
        terminal_outcome="ghost worker dispatch auto-unlocked; retry Run verification",
        refund_attempts=True,
    )
    return True


def recover_post_isolation_lane_b_stall_run(
    run_id: str,
    *,
    actor: str = "workspace_scheduler",
    receipt_summary: str | None = None,
) -> bool:
    """Fail/reopen a worker run stuck after isolation without Lane B progress."""
    from app.persistence import task_store
    from app.runs.service import RunLifecycleError, RunNotFoundError, fail_run
    from app.workspace_agents.worker_dispatch_support import release_worker_dispatch

    cleaned = str(run_id or "").strip()
    if not cleaned:
        return False
    record = run_store.get_run(cleaned)
    if record is None or not run_has_post_isolation_lane_b_stall(record):
        return False
    release_worker_dispatch(cleaned)
    summary = receipt_summary or (
        "Continuous worker dispatch stalled after worker_isolation_created without "
        f"Lane B or verify progress (>{int(ghost_dispatch_seconds())}s); task reopened"
    )
    try:
        fail_run(cleaned, receipt_summary=summary, actor=actor)
    except (RunLifecycleError, RunNotFoundError):
        logger.exception("post-isolation lane B stall recover failed for %s", cleaned)
        return False
    task_store.reopen_orphaned_leased_tasks(
        terminal_run_ids=[cleaned],
        terminal_outcome="worker dispatch stalled after isolation; retry Run verification",
        refund_attempts=True,
    )
    return True


def host_verification_test_active() -> bool:
    """True when a local jest/npm-test process is still running."""
    proc = Path("/proc")
    if not proc.is_dir():
        return False
    try:
        entries = list(proc.iterdir())
    except OSError:
        return False
    for entry in entries:
        name = entry.name
        if not name.isdigit():
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        if not raw:
            continue
        cmdline = raw.replace(b"\x00", b" ").decode("utf-8", errors="ignore")
        if _HOST_VERIFY_CMDLINE_RE.search(cmdline):
            return True
    return False


def _record_is_verification_shift(record: dict[str, Any] | None) -> bool:
    if not isinstance(record, dict):
        return False
    task_id = str(record.get("task_id") or "").strip()
    if not task_id:
        return False
    from app.persistence import task_store
    from app.workspace_agents.verification_execution import is_verification_task

    task = task_store.get_task(task_id)
    return is_verification_task(task)


def _run_has_receipt_type(record: dict[str, Any], receipt_type: str) -> bool:
    history_ref = str(record.get("history_ref") or "").strip()
    if not history_ref:
        return False
    want = receipt_type.strip()
    for item in run_store.list_history(history_ref):
        receipt = item.get("receipt")
        if isinstance(receipt, dict) and str(receipt.get("type") or "").strip() == want:
            return True
    return False


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


def run_looks_like_ota_ship(record: dict[str, Any] | None) -> bool:
    """True when the run summary/detail is an OTA / EAS ship job."""
    if not isinstance(record, dict):
        return False
    blob = " ".join(
        str(record.get(key) or "")
        for key in ("summary", "detail", "current_step")
    )
    return bool(_OTA_RUN_TEXT_RE.search(blob))


def employee_run_stale_seconds_for_record(record: dict[str, Any] | None) -> float:
    """TTL for a concrete run — OTA Lead ships and verification get longer defaults."""
    role = str((record or {}).get("employee_role") or "").strip().lower()
    base = employee_run_stale_seconds_for_role(role)
    if _record_is_verification_shift(record):
        raw = os.environ.get("AXON_WATCH_VERIFICATION_RUN_STALE_SECONDS", "").strip()
        if raw:
            try:
                return max(base, float(raw))
            except ValueError:
                pass
        return max(base, DEFAULT_VERIFICATION_STALE_SECONDS)
    if role != "lead" or not run_looks_like_ota_ship(record):
        return base
    raw = os.environ.get("AXON_WATCH_OTA_LEAD_RUN_STALE_SECONDS", "").strip()
    if raw:
        try:
            return max(base, float(raw))
        except ValueError:
            pass
    return max(base, DEFAULT_OTA_LEAD_STALE_SECONDS)


def host_long_running_ship_active() -> bool:
    """True when a local Expo/EAS/OTA ship process is still running.

    Used as a fail-closed guard so we do not mark Dana's Lead run failed while
    ``expo export`` / ``eas update`` continues (orphaned Cursor shell case).
    """
    proc = Path("/proc")
    if not proc.is_dir():
        return False
    try:
        entries = list(proc.iterdir())
    except OSError:
        return False
    for entry in entries:
        name = entry.name
        if not name.isdigit():
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        if not raw:
            continue
        cmdline = raw.replace(b"\x00", b" ").decode("utf-8", errors="ignore")
        if _HOST_SHIP_CMDLINE_RE.search(cmdline):
            return True
    return False


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


def _normalize_cutoff(
    stale_seconds: float | None,
    *,
    role: str | None = None,
    record: dict[str, Any] | None = None,
) -> float:
    if stale_seconds is not None:
        return max(60.0, float(stale_seconds))
    if record is not None:
        return employee_run_stale_seconds_for_record(record)
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
        cutoff = _normalize_cutoff(stale_seconds, role=role, record=record)
        age = _run_idle_age_seconds(record, now=moment)
        if age is None:
            continue
        run_id = str(record.get("run_id") or "").strip()
        if not run_id:
            continue

        undispatch_cutoff = undispatched_worker_seconds()
        if (
            phase in {"executing", "starting", "planning"}
            and str(record.get("task_id") or "").strip()
            and not _run_has_receipt_type(record, "worker_dispatch_started")
            and age >= undispatch_cutoff
        ):
            from app.persistence import task_store

            try:
                fail_run(
                    run_id,
                    receipt_summary=(
                        "Continuous worker run never received worker_dispatch_started "
                        f"({int(age)}s > {int(undispatch_cutoff)}s)"
                    ),
                    actor="workspace_scheduler",
                )
            except (RunLifecycleError, RunNotFoundError):
                logger.exception("undispatched employee-run reap skipped for %s", run_id)
                continue
            task_store.reopen_orphaned_leased_tasks(
                terminal_run_ids=[run_id],
                terminal_outcome="run failed without worker dispatch; task reopened",
                refund_attempts=True,
            )
            reaped.append(run_id)
            logger.warning(
                "reaped undispatched employee run %s role=%s idle_s=%.0f",
                run_id,
                role,
                age,
            )
            continue

        ghost_cutoff = ghost_dispatch_seconds()
        if (
            phase in {"executing", "starting", "planning"}
            and run_has_ghost_dispatch(record, now=moment)
            and age >= ghost_cutoff
        ):
            if recover_ghost_dispatch_run(
                run_id,
                receipt_summary=(
                    "Ghost worker dispatch auto-unlocked: dispatch started but never "
                    f"reached isolation/progress ({int(age)}s > {int(ghost_cutoff)}s)"
                ),
            ):
                reaped.append(run_id)
                logger.warning(
                    "reaped ghost-dispatch employee run %s role=%s idle_s=%.0f",
                    run_id,
                    role,
                    age,
                )
            continue

        if (
            phase in {"executing", "starting", "planning"}
            and run_has_post_isolation_lane_b_stall(record, now=moment)
        ):
            isolation_age = _isolation_created_age_seconds(record, now=moment) or age
            if recover_post_isolation_lane_b_stall_run(
                run_id,
                receipt_summary=(
                    "Continuous worker dispatch stalled after worker_isolation_created "
                    f"without Lane B progress ({int(isolation_age)}s > "
                    f"{int(ghost_dispatch_seconds())}s)"
                ),
            ):
                reaped.append(run_id)
                logger.warning(
                    "reaped post-isolation lane B stall for %s role=%s idle_s=%.0f",
                    run_id,
                    role,
                    isolation_age,
                )
            continue

        if age < cutoff:
            continue

        # OTA ships often block Cursor shell with no stream chunks — idle age looks
        # dead while expo/eas is still working. Prefer keeping the Lead run alive.
        if (
            phase == "executing"
            and run_looks_like_ota_ship(record)
            and host_long_running_ship_active()
        ):
            logger.info(
                "skipping stale reap for OTA lead run %s — host ship process still active "
                "(idle_s=%.0f cutoff_s=%.0f)",
                run_id,
                age,
                cutoff,
            )
            continue

        if (
            phase == "executing"
            and _record_is_verification_shift(record)
            and host_verification_test_active()
        ):
            logger.info(
                "skipping stale reap for verification run %s — host test process still active "
                "(idle_s=%.0f cutoff_s=%.0f)",
                run_id,
                age,
                cutoff,
            )
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
        if str(record.get("task_id") or "").strip():
            from app.persistence import task_store

            task_store.reopen_orphaned_leased_tasks(
                terminal_run_ids=[run_id],
                terminal_outcome="stale worker run; task reopened for retry",
                refund_attempts=True,
            )
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
    "DEFAULT_OTA_LEAD_STALE_SECONDS",
    "DEFAULT_STALE_SECONDS",
    "employee_run_stale_seconds",
    "employee_run_stale_seconds_for_record",
    "employee_run_stale_seconds_for_role",
    "ghost_dispatch_seconds",
    "host_long_running_ship_active",
    "host_verification_test_active",
    "recover_ghost_dispatch_run",
    "recover_post_isolation_lane_b_stall_run",
    "reap_stale_employee_runs",
    "run_has_dispatch_progress",
    "run_has_ghost_dispatch",
    "run_has_post_isolation_lane_b_stall",
    "run_looks_like_ota_ship",
]
