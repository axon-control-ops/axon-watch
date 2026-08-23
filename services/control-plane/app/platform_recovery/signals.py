"""Multi-signal stale detection. Heartbeat alone is never proof of progress."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.domain.run_state import is_terminal_phase
from app.platform_recovery.checkpoints import checkpoint_is_valid, get_checkpoint
from app.runs.stale_reconcile import (
    _run_idle_age_seconds,
    _STALE_IDLE_SKIP_RECEIPT_TYPES,
    employee_run_stale_seconds_for_record,
    run_has_dispatch_progress,
    run_has_ghost_dispatch,
)

MEANINGFUL_RECEIPT_TYPES = frozenset(
    {
        "worker_progress",
        "worker_delivery",
        "worker_isolation_created",
        "runtime_dispatch",
        "lane_b_invoke_started",
        "verification_terminal_enqueued",
        "phase_transition",
    }
)


def _parse_iso(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def pid_is_alive(pid: int | None) -> bool:
    if not pid or int(pid) <= 0:
        return False
    return Path(f"/proc/{int(pid)}").exists()


def collect_stale_signals(
    record: dict[str, Any],
    *,
    now: datetime | None = None,
    history: list[dict[str, Any]] | None = None,
    lease: dict[str, Any] | None = None,
    worker_pid: int | None = None,
    control_plane_restarted: bool = False,
) -> list[str]:
    phase = str(record.get("phase") or "").strip()
    if is_terminal_phase(phase):
        return []
    moment = now or datetime.now(timezone.utc)
    signals: list[str] = []
    cutoff = employee_run_stale_seconds_for_record(record)
    idle = _run_idle_age_seconds(record, now=moment)
    if idle is not None and idle >= cutoff:
        signals.append("no_meaningful_progress")
    if worker_pid is not None and not pid_is_alive(worker_pid):
        signals.append("process_pid_missing")
    if control_plane_restarted:
        signals.append("control_plane_restart")
    if run_has_ghost_dispatch(record, now=moment):
        signals.append("worker_absent")
    if phase in {"executing", "starting", "planning"} and not run_has_dispatch_progress(record):
        if idle is not None and idle >= 90:
            signals.append("task_running_worker_absent")
    if lease:
        expires = _parse_iso(str(lease.get("lease_expires_at") or ""))
        if expires is not None and expires <= moment:
            signals.append("lease_expired")
        if str(lease.get("status") or "").strip() == "leased" and not str(lease.get("lease_holder") or "").strip():
            signals.append("lease_owner_missing")
    worktree = str((get_checkpoint(str(record.get("run_id") or "")) or {}).get("worktree") or "")
    if worktree and not Path(worktree).exists():
        signals.append("missing_worktree")
    receipt_types = set()
    for item in history or []:
        receipt = item.get("receipt") if isinstance(item, dict) else None
        if isinstance(receipt, dict):
            receipt_types.add(str(receipt.get("type") or "").strip())
    if receipt_types and receipt_types <= _STALE_IDLE_SKIP_RECEIPT_TYPES:
        signals.append("heartbeat_without_progress")
    if MEANINGFUL_RECEIPT_TYPES.isdisjoint(receipt_types) and "worker_heartbeat" in receipt_types:
        if "heartbeat_without_progress" not in signals:
            signals.append("heartbeat_without_progress")
    return signals


def diagnose_stale_run(
    record: dict[str, Any],
    *,
    signals: list[str],
    checkpoint: dict[str, Any] | None = None,
    worker_alive: bool | None = None,
) -> str:
    _ = record
    if not signals:
        return "RUNNING"
    valid = checkpoint_is_valid(checkpoint)
    if "missing_worktree" in signals and not valid:
        return "FAILED"
    stuck = (
        "heartbeat_without_progress" in signals or "no_meaningful_progress" in signals
    )
    if worker_alive is True:
        if stuck or "lease_expired" in signals or "lease_owner_missing" in signals:
            return "RECOVERY_REQUIRED"
        return "RUNNING"
    if worker_alive is False:
        return "RESUMABLE" if valid else "RETRYABLE"
    # Unknown liveness is a stale candidate, not a resume/retry guess.
    return "RECOVERY_REQUIRED"
