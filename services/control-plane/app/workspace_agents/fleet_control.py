"""Fleet control projections for continuous-worker scheduler UI."""

from __future__ import annotations

from typing import Any

from app.persistence import worker_scheduler_settings_store
from app.runs.queries import list_active_employee_runs
from app.runs.service import RunLifecycleError, RunNotFoundError, stop_run
from app.workspace_agents.scheduler import (
    DEFAULT_MAX_ACTIVE_EXECUTING,
    DEFAULT_MAX_STARTS_PER_TICK,
    env_scheduler_allowed,
    run_continuous_worker_tick,
    scheduler_enabled,
    tick_interval_seconds,
    worker_dispatch_enabled_for_status,
)


def build_scheduler_status() -> dict[str, Any]:
    settings = worker_scheduler_settings_store.load_settings()
    env_allowed = env_scheduler_allowed()
    store_enabled = bool(settings.get("scheduler_enabled"))
    effective = scheduler_enabled()
    active_runs = list_active_employee_runs()
    executing_count = sum(
        1 for run in active_runs if str(run.get("phase", "")).strip() == "executing"
    )
    return {
        "scheduler_enabled": store_enabled,
        "effective_enabled": effective,
        "env_allowed": env_allowed,
        "blocked_by_env": not env_allowed,
        "max_active": int(settings.get("max_active") or DEFAULT_MAX_ACTIVE_EXECUTING),
        "max_starts_per_tick": int(
            settings.get("max_starts_per_tick") or DEFAULT_MAX_STARTS_PER_TICK
        ),
        "tick_interval_seconds": tick_interval_seconds(),
        "dispatch_enabled": worker_dispatch_enabled_for_status(),
        "executing_count": executing_count,
        "active_run_count": len(active_runs),
        "employee_enabled": dict(settings.get("employee_enabled") or {}),
        "workspace_enabled": dict(settings.get("workspace_enabled") or {}),
        "updated_at": settings.get("updated_at"),
        # Idle ticks only reconcile housekeeping; Cursor CLI usage starts on dispatch.
        "cursor_usage_on_idle_tick": False,
        "cursor_usage_policy": "dispatch_only",
    }


def _sync_autonomy_with_scheduler(*, enabled: bool) -> None:
    """Workers on ⇒ Full; workers off ⇒ Semi (VAXON stays proactive, not silent Manual)."""
    from app.persistence import operator_presence_settings_store

    current = operator_presence_settings_store.load_settings()
    mode = str(current.get("autonomy_mode") or "manual").strip().lower()
    if enabled and mode != "full":
        operator_presence_settings_store.save_settings({**current, "autonomy_mode": "full"})
    elif not enabled and mode == "full":
        operator_presence_settings_store.save_settings({**current, "autonomy_mode": "semi"})


def patch_scheduler_settings(patch: dict[str, Any]) -> dict[str, Any]:
    worker_scheduler_settings_store.patch_settings(patch)
    if "scheduler_enabled" in patch and patch["scheduler_enabled"] is not None:
        _sync_autonomy_with_scheduler(enabled=bool(patch["scheduler_enabled"]))
    return build_scheduler_status()


def stop_active_runs() -> dict[str, Any]:
    stopped: list[str] = []
    errors: list[dict[str, str]] = []
    for run in list_active_employee_runs():
        run_id = str(run.get("run_id") or "").strip()
        if not run_id:
            continue
        try:
            stop_run(run_id)
            stopped.append(run_id)
        except (RunLifecycleError, RunNotFoundError) as exc:
            errors.append({"run_id": run_id, "error": str(exc)})
    status = build_scheduler_status()
    status["stopped_run_ids"] = stopped
    status["stop_errors"] = errors
    return status


def hard_kill_scheduler() -> dict[str, Any]:
    """Pause continuous starts from Settings (SQLite), stop active shifts, keep VAXON on Semi."""
    worker_scheduler_settings_store.patch_settings({"scheduler_enabled": False})
    _sync_autonomy_with_scheduler(enabled=False)
    status = stop_active_runs()
    status["hard_killed"] = True
    return status


def resume_scheduler() -> dict[str, Any]:
    """Re-enable workers and dispatch queued Lead work without waiting for the next tick."""
    status = patch_scheduler_settings({"scheduler_enabled": True})
    started = run_continuous_worker_tick() if status["effective_enabled"] else []
    status = build_scheduler_status()
    status["resumed"] = True
    status["started_run_ids"] = [
        str(run.get("run_id") or "").strip()
        for run in started
        if str(run.get("run_id") or "").strip()
    ]
    return status


def set_employee_enabled(
    *,
    workspace_id: str,
    role: str,
    enabled: bool,
) -> dict[str, Any]:
    key = worker_scheduler_settings_store.employee_enabled_key(workspace_id, role)
    worker_scheduler_settings_store.patch_settings({"employee_enabled": {key: enabled}})
    return {
        "workspace_id": workspace_id.strip(),
        "role": role.strip().lower(),
        "enabled": bool(enabled),
        "key": key,
    }


def stop_active_runs_for_workspace(workspace_id: str) -> dict[str, Any]:
    """Stop active employee runs for one workspace only."""
    target = str(workspace_id or "").strip()
    stopped: list[str] = []
    errors: list[dict[str, str]] = []
    if not target:
        status = build_scheduler_status()
        status["stopped_run_ids"] = stopped
        status["stop_errors"] = errors
        return status
    for run in list_active_employee_runs():
        if str(run.get("workspace_id") or "").strip() != target:
            continue
        run_id = str(run.get("run_id") or "").strip()
        if not run_id:
            continue
        try:
            stop_run(run_id)
            stopped.append(run_id)
        except (RunLifecycleError, RunNotFoundError) as exc:
            errors.append({"run_id": run_id, "error": str(exc)})
    status = build_scheduler_status()
    status["stopped_run_ids"] = stopped
    status["stop_errors"] = errors
    return status


def set_workspace_enabled(*, workspace_id: str, enabled: bool) -> dict[str, Any]:
    """Arm or pause continuous workers for one workspace from the Workspaces panel."""
    cleaned = str(workspace_id or "").strip()
    if not cleaned:
        raise ValueError("workspace_id is required")
    worker_scheduler_settings_store.patch_settings(
        {"workspace_enabled": {cleaned: bool(enabled)}}
    )
    stopped: dict[str, Any] = {"stopped_run_ids": [], "stop_errors": []}
    if not enabled:
        stopped = stop_active_runs_for_workspace(cleaned)
    status = build_scheduler_status()
    return {
        "workspace_id": cleaned,
        "enabled": bool(enabled),
        "workspace_enabled": dict(status.get("workspace_enabled") or {}),
        "stopped_run_ids": list(stopped.get("stopped_run_ids") or []),
        "stop_errors": list(stopped.get("stop_errors") or []),
        "scheduler": status,
    }
