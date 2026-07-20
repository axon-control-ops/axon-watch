"""Bounded continuous-worker scheduler for always_on / continuous roster roles."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import worker_scheduler_settings_store
from app.runs.service import (
    RunLifecycleError,
    create_run,
    fail_run,
    list_runs,
    prune_terminal_employee_runs,
    reap_abandoned_review_ready_runs,
    reap_stale_employee_runs,
)
from app.runs.stale_reconcile import BUSY_EMPLOYEE_PHASES
from app.workspace_agents.config_loader import EmployeeConfig, load_workspace_agent_configs
from app.workspace_agents.failure_detail import is_usage_limit_failure
from app.workspace_agents.run_outcome import latest_role_run_outcome
from app.workspace_agents.worker_dispatch import dispatch_continuous_worker_run, worker_dispatch_enabled

logger = logging.getLogger(__name__)

CONTINUOUS_SCHEDULES = frozenset({"always_on", "continuous"})
SKIP_ROLES = frozenset({"lead", "overview_agent"})
DEFAULT_TICK_SECONDS = 45.0
# Cap new starts per tick so one restart cannot flood approvals / executing debt.
# Keep these low: each cursor-agent is ~300MB+ and often spawns jest workers.
DEFAULT_MAX_STARTS_PER_TICK = 2
# Skip new starts when non-terminal executing runs already exceed this bound.
# 24 concurrent agents (~7GB+) will thrash past MemoryHigh=3G and trip systemd-oomd.
DEFAULT_MAX_ACTIVE_EXECUTING = 4

_scheduler_task: asyncio.Task[None] | None = None


def env_scheduler_allowed() -> bool:
    """Hard emergency brake from process env (deployment.env / systemd)."""
    raw = os.environ.get("AXON_WATCH_WORKER_SCHEDULER", "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def scheduler_enabled() -> bool:
    """Effective enable: env hard-brake AND SQLite UI overlay."""
    if not env_scheduler_allowed():
        return False
    return bool(worker_scheduler_settings_store.load_settings().get("scheduler_enabled"))


def worker_dispatch_enabled_for_status() -> bool:
    return worker_dispatch_enabled()


def tick_interval_seconds() -> float:
    raw = os.environ.get("AXON_WATCH_WORKER_SCHEDULER_INTERVAL_SECONDS", "").strip()
    if not raw:
        return DEFAULT_TICK_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_TICK_SECONDS
    return max(5.0, value)


def _env_positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(1, value)


def max_starts_per_tick() -> int:
    settings = worker_scheduler_settings_store.load_settings()
    store_value = settings.get("max_starts_per_tick")
    if store_value is not None:
        try:
            return max(1, int(store_value))
        except (TypeError, ValueError):
            pass
    return _env_positive_int(
        "AXON_WATCH_WORKER_SCHEDULER_MAX_STARTS_PER_TICK",
        DEFAULT_MAX_STARTS_PER_TICK,
    )


def max_active_executing() -> int:
    settings = worker_scheduler_settings_store.load_settings()
    store_value = settings.get("max_active")
    if store_value is not None:
        try:
            return max(1, int(store_value))
        except (TypeError, ValueError):
            pass
    return _env_positive_int(
        "AXON_WATCH_WORKER_SCHEDULER_MAX_ACTIVE",
        DEFAULT_MAX_ACTIVE_EXECUTING,
    )


def _usage_limit_blocks_auto_start(workspace_id: str, role: str) -> bool:
    """Skip auto-schedule when the last shift failed on Cursor usage limits."""
    outcome = latest_role_run_outcome(workspace_id, role)
    if not outcome or str(outcome.get("outcome") or "").strip().lower() != "failed":
        return False
    detail = str(outcome.get("detail") or "")
    return is_usage_limit_failure(detail)


def _active_role_run_exists(workspace_id: str, role: str) -> bool:
    """True when a role already has in-flight work (not paused/review leftovers)."""
    cleaned_role = role.strip().lower()
    normalized_workspace = workspace_id.strip()
    for run in list_runs():
        if str(run.get("workspace_id", "")).strip() != normalized_workspace:
            continue
        phase = str(run.get("phase", "")).strip()
        if is_terminal_phase(phase) or phase not in BUSY_EMPLOYEE_PHASES:
            continue
        if str(run.get("employee_role") or "").strip().lower() == cleaned_role:
            return True
    return False


def _executing_run_count() -> int:
    """Count executing employee shifts only — operator runs must not block worker starts."""
    return sum(
        1
        for run in list_runs()
        if str(run.get("phase", "")).strip() == "executing"
        and not is_terminal_phase(str(run.get("phase", "")).strip())
        and str(run.get("employee_role") or "").strip()
    )


def _dispatch_failure_summary(exc: BaseException) -> str:
    message = " ".join(str(exc or "").split()).strip()
    role_hint = "Continuous worker dispatch failed"
    if message:
        return f"{role_hint}: {message}"
    return f"{role_hint} — open run history for receipts."


def _dispatch_worker_run(
    *,
    workspace_id: str,
    employee: EmployeeConfig,
    run_record: dict[str, Any],
) -> None:
    run_id = str(run_record.get("run_id") or "").strip()
    try:
        dispatch_continuous_worker_run(
            workspace_id=workspace_id,
            employee=employee,
            run_record=run_record,
        )
    except Exception as exc:  # noqa: BLE001 — keep scheduler loop alive
        logger.exception(
            "continuous worker dispatch failed for %s role=%s",
            run_id,
            employee.role,
        )
        if not run_id:
            return
        try:
            fail_run(run_id, receipt_summary=_dispatch_failure_summary(exc))
        except RunLifecycleError:
            logger.exception("could not mark worker run failed: %s", run_id)


def run_continuous_worker_tick() -> list[dict[str, Any]]:
    """Reconcile hung shifts, then start bounded role-tagged runs when enabled."""
    reaped = reap_stale_employee_runs()
    if reaped:
        logger.info("continuous worker tick reaped %s stale run(s)", len(reaped))

    abandoned = reap_abandoned_review_ready_runs()
    if abandoned:
        logger.info(
            "continuous worker tick completed %s abandoned review_ready run(s)",
            len(abandoned),
        )

    pruned = prune_terminal_employee_runs()
    if pruned:
        logger.info("continuous worker tick pruned %s terminal employee run(s)", len(pruned))

    if not scheduler_enabled():
        return []

    _configs, _defaults, companies, _staffing = load_workspace_agent_configs()
    active_bound = max_active_executing()
    if _executing_run_count() >= active_bound:
        logger.info(
            "continuous worker tick skipped: executing debt bound reached (%s)",
            active_bound,
        )
        return []

    starts_bound = max_starts_per_tick()
    started: list[dict[str, Any]] = []
    for workspace_id, company in companies.items():
        for employee in company.employees:
            if len(started) >= starts_bound:
                return started
            role = str(employee.role or "").strip().lower()
            if not worker_scheduler_settings_store.is_employee_enabled(
                workspace_id,
                role,
                file_enabled=bool(employee.enabled),
            ):
                continue
            schedule = str(employee.schedule or "").strip().lower()
            if not role or role in SKIP_ROLES:
                continue
            if schedule not in CONTINUOUS_SCHEDULES:
                continue
            if _active_role_run_exists(workspace_id, role):
                continue
            if _usage_limit_blocks_auto_start(workspace_id, role):
                logger.info(
                    "continuous worker tick skipped role=%s workspace=%s: usage limits blocked last shift",
                    role,
                    workspace_id,
                )
                continue

            name = str(employee.name or role).strip() or role
            record = create_run(
                workspace_id=workspace_id,
                mode="agent",
                summary=f"{name}: continuous worker shift",
                detail=(
                    f"Bounded scheduled work for role={role} schedule={schedule} "
                    f"workspace={workspace_id}"
                ),
                employee_role=role,
                requires_approval=False,
            )
            started.append(record)
            if worker_dispatch_enabled():
                threading.Thread(
                    target=_dispatch_worker_run,
                    kwargs={
                        "workspace_id": workspace_id,
                        "employee": employee,
                        "run_record": record,
                    },
                    daemon=True,
                    name=f"worker-dispatch-{record.get('run_id')}",
                ).start()
    return started


async def _scheduler_loop() -> None:
    interval = tick_interval_seconds()
    # Delay the first tick so short-lived TestClient sessions stay clean.
    await asyncio.sleep(interval)
    while True:
        try:
            started = await asyncio.to_thread(run_continuous_worker_tick)
            if started:
                logger.info("continuous worker tick started %s run(s)", len(started))
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — keep the loop alive across tick failures
            logger.exception("continuous worker tick failed")
        await asyncio.sleep(interval)


async def start_continuous_worker_scheduler() -> asyncio.Task[None] | None:
    """Start the periodic tick; cancel via stop_continuous_worker_scheduler.

    The loop always runs so Settings can enable workers without a process restart.
    Each tick always reconciles stale/abandoned/pruned runs; new starts only when
    scheduler_enabled() is true (env brake and/or UI off).
    """
    global _scheduler_task
    if _scheduler_task is not None and not _scheduler_task.done():
        return _scheduler_task
    _scheduler_task = asyncio.create_task(
        _scheduler_loop(),
        name="continuous-worker-scheduler",
    )
    return _scheduler_task


async def stop_continuous_worker_scheduler(
    task: asyncio.Task[None] | None = None,
) -> None:
    global _scheduler_task
    target = task if task is not None else _scheduler_task
    _scheduler_task = None
    if target is None:
        return
    target.cancel()
    try:
        await target
    except asyncio.CancelledError:
        return
