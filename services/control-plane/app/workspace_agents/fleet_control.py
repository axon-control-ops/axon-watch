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
        "updated_at": settings.get("updated_at"),
    }


def patch_scheduler_settings(patch: dict[str, Any]) -> dict[str, Any]:
    worker_scheduler_settings_store.patch_settings(patch)
    if "scheduler_enabled" in patch and patch["scheduler_enabled"] is not None:
        # Keep presence autonomy_mode aligned with the fleet master switch.
        from app.persistence import operator_presence_settings_store

        current = operator_presence_settings_store.load_settings()
        mode = str(current.get("autonomy_mode") or "manual").strip().lower()
        enabled = bool(patch["scheduler_enabled"])
        if enabled and mode != "full":
            operator_presence_settings_store.save_settings({**current, "autonomy_mode": "full"})
        elif not enabled and mode == "full":
            operator_presence_settings_store.save_settings({**current, "autonomy_mode": "semi"})
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
