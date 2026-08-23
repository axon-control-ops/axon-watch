"""Recovery Center projection from durable run, task, lease, and checkpoint state."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import run_store, task_store
from app.platform_recovery.checkpoints import checkpoint_is_valid, get_checkpoint
from app.platform_recovery.classifier import classify_run_record
from app.platform_recovery.next_action import describe_next_action
from app.platform_recovery.signals import collect_stale_signals, diagnose_stale_run
from app.platform_recovery.store import list_recovery_records, upsert_recovery_record
from app.runs.stale_reconcile import BUSY_EMPLOYEE_PHASES, _run_idle_age_seconds

_BUCKET_FROM_OUTCOME = {
    "RUNNING": "ACTIVE",
    "RECOVERY_REQUIRED": "STALE",
    "RESUMABLE": "RESUMABLE",
    "RETRYABLE": "RETRYABLE",
    "FAILED": "FAILED",
    "HUMAN_REVIEW": "HUMAN_REVIEW",
}
_TERMINAL_ATTENTION_WINDOW = timedelta(hours=24)


def _parse_timestamp(value: Any) -> datetime | None:
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


def _attention_key(record: dict[str, Any]) -> tuple[str, str]:
    workspace = str(record.get("workspace_id") or "")
    role = str(record.get("employee_role") or "").strip() or "interactive"
    return workspace, role


def _select_actionable_records(
    records: list[dict[str, Any]],
    *,
    now: datetime,
) -> list[dict[str, Any]]:
    """Keep active work plus one recent terminal outcome per workspace/agent.

    Durable run history remains in the run store. Recovery Center is the live
    action queue, not a second unbounded history browser.
    """
    live: list[dict[str, Any]] = []
    latest_terminal: dict[tuple[str, str], tuple[datetime, dict[str, Any]]] = {}
    live_keys: set[tuple[str, str]] = set()
    for record in records:
        phase = str(record.get("phase") or "")
        if not is_terminal_phase(phase):
            live.append(record)
            live_keys.add(_attention_key(record))
            continue
        stamp = _parse_timestamp(record.get("ended_at") or record.get("updated_at"))
        if stamp is None or now - stamp > _TERMINAL_ATTENTION_WINDOW:
            continue
        key = _attention_key(record)
        previous = latest_terminal.get(key)
        if previous is None or stamp > previous[0]:
            latest_terminal[key] = (stamp, record)
    terminal = [
        pair[1]
        for key, pair in latest_terminal.items()
        if key not in live_keys
    ]
    return live + terminal


def _history(record: dict[str, Any]) -> list[dict[str, Any]]:
    history_ref = str(record.get("history_ref") or "").strip()
    if not history_ref:
        return []
    return list(run_store.list_history(history_ref))


def _lease_view(task: dict[str, Any] | None) -> dict[str, Any] | None:
    if not task:
        return None
    return {
        "owner": task.get("lease_holder"),
        "created_at": task.get("created_at"),
        "expires_at": task.get("lease_expires_at"),
        "state": task.get("status"),
        "run_id": task.get("run_id"),
        "attempts_used": task.get("attempts_used"),
        "attempt_budget": task.get("attempt_budget"),
    }


def project_run_item(record: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    moment = now or datetime.now(timezone.utc)
    history = _history(record)
    task_id = str(record.get("task_id") or "").strip()
    task = task_store.get_task(task_id) if task_id else None
    lease = _lease_view(task)
    checkpoint = get_checkpoint(str(record.get("run_id") or ""))
    signals = collect_stale_signals(
        record, now=moment, history=history, lease=task,
    )
    outcome = diagnose_stale_run(
        record,
        signals=signals,
        checkpoint=checkpoint,
        worker_alive=None if signals else True,
    )
    phase = str(record.get("phase") or "")
    if is_terminal_phase(phase):
        if phase == "failed":
            outcome = "FAILED"
        elif phase == "cancelled":
            outcome = "RETRYABLE"
    elif phase == "paused" and checkpoint_is_valid(checkpoint):
        outcome = "RESUMABLE"
    elif phase == "paused":
        outcome = "RETRYABLE"
    failure_class = classify_run_record(record, history=history)
    idle = _run_idle_age_seconds(record, now=moment)
    retry_remaining = 0
    if task:
        budget = int(task.get("attempt_budget") or 0)
        used = int(task.get("attempts_used") or 0)
        retry_remaining = max(0, budget - used)
    bucket = _BUCKET_FROM_OUTCOME.get(outcome, "HUMAN_REVIEW")
    if phase == "awaiting_approval":
        bucket = "BLOCKED"
    next_action = describe_next_action(
        bucket=bucket,
        failure_class=failure_class,
        checkpoint_valid=checkpoint_is_valid(checkpoint),
        retry_remaining=retry_remaining,
        idle_seconds=idle,
    )
    why = ", ".join(signals) if signals else "no stale signals"
    return {
        "run_id": record.get("run_id"),
        "task_id": task_id or None,
        "workspace_id": record.get("workspace_id"),
        "agent": record.get("employee_role") or record.get("actor") or "",
        "phase": record.get("phase"),
        "bucket": bucket,
        "failure_class": failure_class,
        "what_happened": str(record.get("current_step") or record.get("summary") or ""),
        "why_stale": why,
        "last_meaningful_progress": (checkpoint or {}).get("last_meaningful_progress_at"),
        "last_heartbeat": record.get("updated_at"),
        "current_worker": (lease or {}).get("owner"),
        "current_lease": lease,
        "current_checkpoint": checkpoint,
        "files_changed": (checkpoint or {}).get("changed_paths") or [],
        "last_known_provider": (checkpoint or {}).get("execution_provider") or "",
        "retry_count": int((task or {}).get("attempts_used") or 0),
        "recovery_action": next_action,
        "evidence": {
            "signals": signals,
            "diagnostic": outcome,
            "history_ref": record.get("history_ref"),
        },
        "actions": _actions_for(bucket),
    }


def _actions_for(bucket: str) -> list[str]:
    mapping = {
        "ACTIVE": ["Inspect", "Open Logs", "Open Evidence"],
        "STALE": ["Inspect", "Reconcile", "Resume", "Retry", "Cancel", "Open Evidence", "Acknowledge"],
        "ORPHANED": ["Inspect", "Reconcile", "Cancel", "Open Evidence", "Acknowledge"],
        "RESUMABLE": ["Inspect", "Resume", "Open Worktree", "Open Evidence"],
        "RETRYABLE": ["Inspect", "Retry", "Cancel", "Open Evidence", "Acknowledge"],
        "FAILED": ["Inspect", "Open Logs", "Open Evidence", "Open Verification", "Acknowledge"],
        "BLOCKED": ["Inspect", "Approve", "Open Evidence", "Acknowledge"],
        "HUMAN_REVIEW": ["Inspect", "Open Evidence", "Acknowledge"],
    }
    return mapping.get(bucket, ["Inspect", "Acknowledge"])


def build_recovery_center(
    *,
    workspace_id: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    moment = datetime.now(timezone.utc)
    items: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for record in run_store.list_runs():
        phase = str(record.get("phase") or "")
        if workspace_id and str(record.get("workspace_id") or "") != workspace_id:
            continue
        if phase not in BUSY_EMPLOYEE_PHASES and phase not in {
            "paused", "awaiting_approval", "failed", "cancelled", "review_ready",
        }:
            if phase == "completed":
                continue
        candidates.append(record)
    for record in _select_actionable_records(candidates, now=moment):
        phase = str(record.get("phase") or "")
        item = project_run_item(record, now=moment)
        if item["bucket"] == "ACTIVE" and phase not in BUSY_EMPLOYEE_PHASES:
            continue
        if persist:
            stored = upsert_recovery_record(
                {
                    "run_id": item.get("run_id"),
                    "task_id": item.get("task_id"),
                    "workspace_id": item.get("workspace_id") or "",
                    "bucket": item["bucket"],
                    "failure_class": item["failure_class"],
                    "recovery_state": item["bucket"],
                    "what_happened": item["what_happened"],
                    "why_stale": item["why_stale"],
                    "next_action": item["recovery_action"]["summary"],
                    "evidence": item["evidence"],
                    "idempotency_key": f"run:{item.get('run_id')}",
                }
            )
            item["recovery_id"] = stored.get("recovery_id")
            item["acknowledged"] = bool(stored.get("acknowledged"))
        else:
            item["acknowledged"] = False
        item["actionable"] = (
            item["bucket"] in {
                "STALE", "ORPHANED", "RESUMABLE", "RETRYABLE",
                "FAILED", "BLOCKED", "HUMAN_REVIEW",
            }
            and not item["acknowledged"]
        )
        items.append(item)
    persisted = list_recovery_records()
    counts: dict[str, int] = {}
    for item in items:
        counts[item["bucket"]] = counts.get(item["bucket"], 0) + 1
    attention_buckets = {
        "STALE", "ORPHANED", "RESUMABLE", "RETRYABLE",
        "FAILED", "BLOCKED", "HUMAN_REVIEW",
    }
    attention = sum(
        1
        for item in items
        if item["bucket"] in attention_buckets and not item.get("acknowledged")
    )
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "attention_count": attention,
        "counts": counts,
        "items": items,
        "persisted": persisted,
    }
