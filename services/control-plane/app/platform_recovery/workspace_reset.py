"""Guarded workspace recovery reset that preserves durable audit evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import run_store, task_store
from app.platform_recovery.projection import build_recovery_center
from app.platform_recovery.store import acknowledge_recovery
from app.runs.service import RunLifecycleError, RunNotFoundError, fail_run, stop_run

_RESET_BUCKETS = frozenset(
    {
        "STALE",
        "ORPHANED",
        "RESUMABLE",
        "RETRYABLE",
        "FAILED",
        "BLOCKED",
        "HUMAN_REVIEW",
    }
)
_ACTIVE_TASK_STATUSES = frozenset({"open", "leased"})
_ORPHANED_LEASE_GRACE = timedelta(minutes=5)


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


def _is_orphaned_leased_task(task: dict[str, Any], *, now: datetime) -> bool:
    if str(task.get("status") or "").strip().lower() != "leased":
        return False
    expires = _parse_timestamp(task.get("lease_expires_at"))
    if expires is not None and expires <= now:
        return True
    updated = _parse_timestamp(task.get("updated_at"))
    if updated is None or now - updated < _ORPHANED_LEASE_GRACE:
        return False
    run_id = str(task.get("run_id") or "").strip()
    if not run_id:
        return True
    run = run_store.get_run(run_id)
    return run is None or is_terminal_phase(str(run.get("phase") or ""))


def _reset_candidates(workspace_id: str) -> dict[str, Any]:
    workspace = str(workspace_id or "").strip()
    if not workspace:
        raise ValueError("workspace_id is required")

    snapshot = build_recovery_center(workspace_id=workspace, persist=True)
    items = [
        item
        for item in snapshot.get("items") or []
        if item.get("actionable") and str(item.get("bucket") or "") in _RESET_BUCKETS
    ]
    run_ids = sorted(
        {
            str(item.get("run_id") or "").strip()
            for item in items
            if str(item.get("run_id") or "").strip()
        }
    )
    recovery_ids = sorted(
        {
            str(item.get("recovery_id") or "").strip()
            for item in items
            if str(item.get("recovery_id") or "").strip()
        }
    )
    linked_task_ids = {
        str(item.get("task_id") or "").strip()
        for item in items
        if str(item.get("task_id") or "").strip()
    }
    task_ids: set[str] = set()
    for task_id in sorted(linked_task_ids):
        task = task_store.get_task(task_id)
        if task is None:
            continue
        if str(task.get("workspace_id") or "").strip() != workspace:
            continue
        if str(task.get("status") or "").strip().lower() in _ACTIVE_TASK_STATUSES:
            task_ids.add(task_id)

    orphaned_task_ids: set[str] = set()
    now = datetime.now(timezone.utc)
    for task in task_store.list_tasks(workspace_id=workspace, limit=500):
        if not _is_orphaned_leased_task(task, now=now):
            continue
        task_id = str(task.get("task_id") or "").strip()
        if task_id:
            task_ids.add(task_id)
            orphaned_task_ids.add(task_id)

    return {
        "workspace_id": workspace,
        "items": items,
        "run_ids": run_ids,
        "task_ids": sorted(task_ids),
        "orphaned_task_ids": sorted(orphaned_task_ids),
        "recovery_ids": recovery_ids,
    }


def _cancel_live_run(run_id: str) -> dict[str, Any] | None:
    record = run_store.get_run(run_id)
    if record is None or is_terminal_phase(str(record.get("phase") or "")):
        return None
    try:
        if str(record.get("phase") or "") == "review_ready":
            return fail_run(
                run_id,
                receipt_summary="Run closed by guarded workspace recovery reset",
                actor="operator",
            )
        stopped = stop_run(run_id)
        if str(stopped.get("phase") or "") == "paused":
            stopped = stop_run(run_id)
        return stopped
    except (RunLifecycleError, RunNotFoundError):
        return None


def reset_workspace_recovery_state(
    workspace_id: str,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    """Preview or resolve the selected workspace's actionable recovery queue.

    Execute cancels only tasks linked to the visible failed/stale recovery items,
    stops any corresponding live runs, and acknowledges those recovery records.
    Run history, checkpoints, worktrees, and terminal evidence are retained.
    """

    candidates = _reset_candidates(workspace_id)
    response: dict[str, Any] = {
        "mode": "EXECUTE" if execute else "DRY_RUN",
        "workspace_id": candidates["workspace_id"],
        "run_ids": candidates["run_ids"],
        "task_ids": candidates["task_ids"],
        "recovery_ids": candidates["recovery_ids"],
        "candidate_count": len(candidates["items"])
        + len(
            set(candidates["orphaned_task_ids"])
            - {
                str(item.get("task_id") or "").strip()
                for item in candidates["items"]
                if str(item.get("task_id") or "").strip()
            }
        ),
        "orphaned_task_ids": candidates["orphaned_task_ids"],
        "cancelled_runs": [],
        "cancelled_tasks": [],
        "acknowledged_recoveries": [],
        "errors": [],
        "preserved": ["run_history", "checkpoints", "worktrees", "terminal_evidence"],
    }
    if not execute:
        return response

    for run_id in candidates["run_ids"]:
        record = run_store.get_run(run_id)
        if record is None or is_terminal_phase(str(record.get("phase") or "")):
            continue
        stopped = _cancel_live_run(run_id)
        if stopped is None:
            response["errors"].append(
                {"kind": "run", "id": run_id, "detail": "run could not be stopped"}
            )
        else:
            response["cancelled_runs"].append(run_id)

    for task_id in candidates["task_ids"]:
        try:
            task_store.cancel_task(
                task_id,
                terminal_outcome="cancelled by guarded workspace recovery reset",
            )
        except task_store.TaskLedgerError as exc:
            response["errors"].append(
                {"kind": "task", "id": task_id, "detail": str(exc)}
            )
        else:
            response["cancelled_tasks"].append(task_id)

    for recovery_id in candidates["recovery_ids"]:
        if acknowledge_recovery(recovery_id) is None:
            response["errors"].append(
                {"kind": "recovery", "id": recovery_id, "detail": "record not found"}
            )
        else:
            response["acknowledged_recoveries"].append(recovery_id)

    return response


__all__ = ["reset_workspace_recovery_state"]
