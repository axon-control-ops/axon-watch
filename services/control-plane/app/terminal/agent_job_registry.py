"""In-memory record store for Axon agent terminal jobs.

Holds job state plus the watcher handles (PTY unsubscribe, deadline timer,
interrupt callback) so ``agent_jobs`` and ``agent_job_watcher`` share one
source of truth for whether a job is still live.
"""

from __future__ import annotations

import threading
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable

from app.terminal.agent_job_chat import reset_live_job_fences

_MAX_OUTPUT_TAIL_CHARS = 20_000
TERMINAL_STATUSES = frozenset({"completed", "failed", "timed_out", "cancelled"})

_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}
_job_unsubscribers: dict[str, Callable[[], None]] = {}
_job_timers: dict[str, threading.Timer] = {}
_job_interrupts: dict[str, Callable[..., None]] = {}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def register_job(record: dict[str, Any]) -> None:
    with _lock:
        _jobs[str(record["job_id"])] = record


def append_job_output_tail(job_id: str, text: str) -> None:
    if not text:
        return
    with _lock:
        record = _jobs.get(job_id)
        if record is None:
            return
        existing = str(record.get("output_tail") or "")
        record["output_tail"] = (existing + text)[-_MAX_OUTPUT_TAIL_CHARS:]


def mark_job_finished(
    job_id: str,
    *,
    status: str,
    exit_code: int | None,
    note: str = "",
) -> None:
    """Record a terminal state, unless the job already reached one."""
    with _lock:
        record = _jobs.get(job_id)
        if record is None or str(record.get("status") or "") in TERMINAL_STATUSES:
            return
        record["status"] = status
        record["exit_code"] = exit_code
        record["finished_at"] = utc_now()
        if note:
            record["failure_reason"] = note


def store_job_watcher(
    job_id: str,
    *,
    unsubscribe: Callable[[], None],
    timer: threading.Timer,
    interrupt: Callable[..., None],
) -> None:
    with _lock:
        _job_unsubscribers[job_id] = unsubscribe
        _job_timers[job_id] = timer
        _job_interrupts[job_id] = interrupt


def job_interrupt(job_id: str) -> Callable[..., None] | None:
    with _lock:
        return _job_interrupts.get(job_id)


def release_job_watcher(job_id: str) -> None:
    with _lock:
        timer = _job_timers.pop(job_id, None)
        unsub = _job_unsubscribers.pop(job_id, None)
        _job_interrupts.pop(job_id, None)
    if timer is not None:
        timer.cancel()
    if unsub is not None:
        try:
            unsub()
        except Exception:  # noqa: BLE001 - listener teardown is best effort
            pass


def set_job_receipt(job_id: str, receipt: str) -> dict[str, Any] | None:
    """Attach the receipt without clobbering state the watcher already wrote."""
    with _lock:
        record = _jobs.get(job_id)
        if record is None:
            return None
        record["receipt"] = receipt
        return deepcopy(record)


def get_agent_terminal_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        record = _jobs.get(str(job_id or "").strip())
        return deepcopy(record) if record is not None else None


def list_agent_terminal_jobs(workspace_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    clean = str(workspace_id or "").strip()
    with _lock:
        items = [
            deepcopy(record)
            for record in _jobs.values()
            if str(record.get("workspace_id") or "") == clean
        ]
    items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return items[: max(1, min(int(limit), 100))]


def reset_agent_terminal_jobs() -> None:
    with _lock:
        unsubs = list(_job_unsubscribers.values())
        timers = list(_job_timers.values())
        _job_unsubscribers.clear()
        _job_timers.clear()
        _job_interrupts.clear()
        _jobs.clear()
    for timer in timers:
        timer.cancel()
    for unsub in unsubs:
        try:
            unsub()
        except Exception:  # noqa: BLE001
            pass
    reset_live_job_fences()


__all__ = [
    "TERMINAL_STATUSES",
    "append_job_output_tail",
    "get_agent_terminal_job",
    "job_interrupt",
    "list_agent_terminal_jobs",
    "mark_job_finished",
    "register_job",
    "release_job_watcher",
    "reset_agent_terminal_jobs",
    "set_job_receipt",
    "store_job_watcher",
    "utc_now",
]
