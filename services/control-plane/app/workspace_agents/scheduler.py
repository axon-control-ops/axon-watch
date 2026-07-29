"""Bounded continuous-worker scheduler for always_on / continuous roster roles."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import task_store, worker_scheduler_settings_store
from app.runs.begin_execution import begin_execution
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
from app.workspace_agents.scheduler_auto_start_gates import (
    runtime_auth_blocks_auto_start,
    usage_limit_blocks_auto_start,
)
from app.workspace_agents.worker_dispatch import dispatch_continuous_worker_run, worker_dispatch_enabled

logger = logging.getLogger(__name__)

CONTINUOUS_SCHEDULES = frozenset({"always_on", "continuous"})
SKIP_ROLES = frozenset({"lead", "overview_agent"})
DEFAULT_TICK_SECONDS = 45.0
# Cap new starts per tick so one restart cannot flood approvals / executing debt.
# Keep these low: each cursor-agent is ~300MB+ and often spawns jest / tsserver workers.
DEFAULT_MAX_STARTS_PER_TICK = 1
# Skip new starts when non-terminal executing runs already exceed this bound.
# 3+ concurrent agents with jest/tsserver thrash past MemoryHigh and trip systemd-oomd.
DEFAULT_MAX_ACTIVE_EXECUTING = 2

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


def _employee_for_role(
    companies: dict[str, Any],
    workspace_id: str,
    role: str,
) -> EmployeeConfig | None:
    company = companies.get(workspace_id)
    if company is None:
        return None
    want = role.strip().lower()
    for employee in company.employees:
        if str(employee.role or "").strip().lower() == want:
            return employee
    return None


def _dispatch_queued_lead_fan_out_runs(
    *,
    companies: dict[str, Any],
    starts_bound: int,
    active_bound: int,
) -> list[dict[str, Any]]:
    """Promote Lead fan-out queued runs into Lane B without creating duplicate runs."""
    if not worker_dispatch_enabled() or starts_bound <= 0:
        return []
    started: list[dict[str, Any]] = []
    queued = [
        run
        for run in list_runs()
        if str(run.get("phase") or "").strip() == "queued"
        and str(run.get("employee_role") or "").strip()
        and str(run.get("task_id") or "").strip()
        and not is_terminal_phase(str(run.get("phase") or "").strip())
    ]
    queued.sort(key=lambda run: str(run.get("started_at") or run.get("updated_at") or ""))
    for run in queued:
        if len(started) >= starts_bound:
            break
        if _executing_run_count() + len(started) >= active_bound:
            break
        workspace_id = str(run.get("workspace_id") or "").strip()
        role = str(run.get("employee_role") or "").strip().lower()
        employee = _employee_for_role(companies, workspace_id, role)
        if employee is None:
            continue
        if not worker_scheduler_settings_store.is_employee_enabled(
            workspace_id,
            role,
            file_enabled=bool(employee.enabled),
        ):
            continue
        try:
            advanced = begin_execution(
                str(run["run_id"]),
                actor="workspace_scheduler",
                receipt_summary="Queued fan-out run entered execution for dispatch",
            )
        except RunLifecycleError:
            logger.exception("could not advance queued fan-out run %s", run.get("run_id"))
            continue
        started.append(advanced)
        threading.Thread(
            target=_dispatch_worker_run,
            kwargs={
                "workspace_id": workspace_id,
                "employee": employee,
                "run_record": advanced,
            },
            daemon=True,
            name=f"worker-dispatch-queued-{advanced.get('run_id')}",
        ).start()
    return started


def run_continuous_worker_tick(
    *,
    starts_bound_override: int | None = None,
) -> list[dict[str, Any]]:
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

    try:
        from app.workspace_delivery.poll import poll_pending_deliveries

        timed_out = poll_pending_deliveries()
        if timed_out:
            logger.info("workspace delivery poll updated %s delivery(ies)", len(timed_out))
    except Exception:  # noqa: BLE001 — never block scheduler on delivery poll
        logger.exception("workspace delivery poll failed")

    work_source_result: dict[str, Any] = {}
    try:
        from app.workspace_agents.company_work_sources import run_scheduled_work_sources

        work_source_result = run_scheduled_work_sources()
        recovered = work_source_result.get("recovered_leases") or []
        if recovered:
            logger.info(
                "continuous worker tick recovered %s orphaned leased task(s)",
                len(recovered),
            )
        patrol = (work_source_result.get("sources") or {}).get("file_size_patrol") or {}
        created = patrol.get("created_tasks") or []
        if created:
            logger.info(
                "continuous worker tick enqueued %s file-size patrol task(s)",
                len(created),
            )
    except Exception:  # noqa: BLE001 — never block scheduler on work sources
        logger.exception("scheduled company work sources failed")

    if not scheduler_enabled():
        return []

    _configs, _defaults, companies, _staffing = load_workspace_agent_configs()
    active_bound = max_active_executing()
    executing = _executing_run_count()
    if executing >= active_bound:
        logger.info(
            "continuous worker tick skipped: executing debt bound reached (%s)",
            active_bound,
        )
        return []

    free_slots = max(0, active_bound - executing)
    default_starts = max_starts_per_tick()
    if starts_bound_override is not None:
        try:
            starts_bound = max(1, int(starts_bound_override))
        except (TypeError, ValueError):
            starts_bound = default_starts
    else:
        starts_bound = default_starts
    starts_bound = min(starts_bound, free_slots)
    started: list[dict[str, Any]] = _dispatch_queued_lead_fan_out_runs(
        companies=companies,
        starts_bound=starts_bound,
        active_bound=active_bound,
    )
    if len(started) >= starts_bound:
        return started
    for workspace_id, company in companies.items():
        for employee in company.employees:
            if len(started) >= starts_bound:
                return started
            if _executing_run_count() + len(started) >= active_bound:
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
            if usage_limit_blocks_auto_start(workspace_id, role):
                logger.info(
                    "continuous worker tick skipped role=%s workspace=%s: "
                    "Cursor usage limits blocked this role's last shift",
                    role,
                    workspace_id,
                )
                continue
            if runtime_auth_blocks_auto_start(workspace_id, role):
                logger.info(
                    "continuous worker tick skipped role=%s workspace=%s: runtime auth blocked last shift",
                    role,
                    workspace_id,
                )
                continue

            name = str(employee.name or role).strip() or role
            lease_holder = f"employee-{workspace_id}-{role}"
            claimed = task_store.claim_open_task_for_role(
                workspace_id=workspace_id,
                owner_role=role,
                lease_holder=lease_holder,
            )
            if claimed is None:
                logger.info(
                    "continuous worker tick skipped role=%s workspace=%s: no open leased task",
                    role,
                    workspace_id,
                )
                continue
            from app.workspace_agents.autonomous_attention_policy import (
                task_allows_autonomous_lease,
            )

            lease_decision = task_allows_autonomous_lease(claimed)
            if lease_decision.tier != "auto_safe" or lease_decision.decision != "dispatch":
                task_id = str(claimed.get("task_id") or "").strip()
                logger.warning(
                    "continuous worker tick refused gated task=%s role=%s reason=%s",
                    task_id,
                    role,
                    lease_decision.reason,
                )
                if task_id:
                    try:
                        task_store.cancel_task(
                            task_id,
                            terminal_outcome=(
                                f"autonomous lease refused: {lease_decision.reason}"
                            ),
                        )
                    except task_store.TaskLedgerError:
                        logger.exception(
                            "could not cancel gated task after lease refuse: %s",
                            task_id,
                        )
                continue
            task_id = str(claimed.get("task_id") or "").strip()
            goal = str(claimed.get("goal") or "").strip() or "leased task"
            try:
                record = create_run(
                    workspace_id=workspace_id,
                    mode="agent",
                    summary=f"{name}: {goal[:80]}",
                    detail=(
                        f"Bounded scheduled work for role={role} schedule={schedule} "
                        f"workspace={workspace_id} task={task_id}"
                    ),
                    employee_role=role,
                    task_id=task_id,
                    require_leased_task=True,
                    requires_approval=False,
                )
            except RunLifecycleError as exc:
                logger.warning(
                    "continuous worker tick could not start role=%s task=%s: %s",
                    role,
                    task_id,
                    exc,
                )
                try:
                    task_store.fail_task(
                        task_id,
                        terminal_outcome=f"create_run refused: {exc}",
                        reopen_if_budget_remaining=True,
                    )
                except task_store.TaskLedgerError:
                    logger.exception("could not reopen task after create_run refuse: %s", task_id)
                continue
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
