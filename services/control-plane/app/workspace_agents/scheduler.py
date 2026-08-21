"""Bounded continuous-worker scheduler for always_on / continuous roster roles."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import task_store, worker_scheduler_settings_store
from app.runs.service import (
    RunLifecycleError,
    create_run,
    fail_run,
    list_runs,
    prune_terminal_employee_runs,
    reap_abandoned_review_ready_runs,
    reap_stale_employee_runs,
    reap_stale_interactive_runs,
    reconcile_employee_runs_missing_tasks,
)
from app.runs.stale_reconcile import BUSY_EMPLOYEE_PHASES
from app.workspace_agents.isolation_reaper import reap_abandoned_worker_isolations
from app.workspace_agents.config_loader import EmployeeConfig, load_workspace_agent_configs
from app.workspace_agents.scheduler_auto_start_gates import (
    continuous_auto_start_skip_reason,
)
from app.workspace_agents.scheduler_attention_scan import run_due_attention_scan_and_log
from app.workspace_agents.scheduler_queued_fan_out import dispatch_queued_lead_fan_out_runs
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


def env_observation_scheduler_allowed() -> bool:
    """Hard brake for read-mostly watcher observation ticks.

    Defaults on, independent from the worker/action scheduler. Set
    AXON_WATCH_OBSERVATION_SCHEDULER=0 only when even polling/reconciliation
    should stop.
    """
    raw = os.environ.get("AXON_WATCH_OBSERVATION_SCHEDULER", "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def observation_scheduler_enabled() -> bool:
    """Effective watcher enable: observation env brake AND SQLite UI overlay."""
    if not env_observation_scheduler_allowed():
        return False
    return bool(
        worker_scheduler_settings_store.load_settings().get(
            "watcher_scheduler_enabled",
            True,
        )
    )


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


def _trace_scheduler_lease_decision(
    *,
    task: dict[str, Any],
    decision: str,
    tier: str,
    risk: str,
    explanation: str,
    run_id: str | None = None,
) -> None:
    """Best-effort constitution trace for scheduler lease decisions.

    The task ledger and run history remain the source of truth. Constitution
    indexing is deliberately non-blocking so the worker scheduler does not fail
    closed because an executive/audit registry write failed.
    """
    task_id = str(task.get("task_id") or "").strip()
    workspace_id = str(task.get("workspace_id") or "").strip()
    if not task_id:
        return
    try:
        from app.persistence import constitution_registry_store as registry

        evidence = registry.index_evidence(
            source_table="workspace_tasks",
            source_id=task_id,
            source_ref={
                "task_id": task_id,
                "owner_role": str(task.get("owner_role") or "").strip(),
                "status": str(task.get("status") or "").strip(),
            },
            kind="scheduler_lease_decision",
            summary=str(task.get("goal") or "Scheduler leased task").strip(),
            workspace_id=workspace_id,
            run_id=run_id,
            task_id=task_id,
            tags=["worker_scheduler", decision, tier, risk],
        )
        recorded = registry.record_decision(
            actor="worker_scheduler",
            capability_id="CAP-034",
            decision=decision,
            tier=tier,
            risk=risk,
            explanation=explanation,
            confidence_note="deterministic scheduler lease policy",
            task_id=task_id,
            run_id=run_id,
            source_table="workspace_tasks",
            source_id=task_id,
            evidence_ids=[str(evidence["evidence_id"])],
        )
        registry.index_evidence(
            source_table="workspace_tasks",
            source_id=task_id,
            source_ref={
                "task_id": task_id,
                "owner_role": str(task.get("owner_role") or "").strip(),
                "status": str(task.get("status") or "").strip(),
            },
            kind="scheduler_lease_decision",
            summary=str(task.get("goal") or "Scheduler leased task").strip(),
            workspace_id=workspace_id,
            run_id=run_id,
            task_id=task_id,
            decision_id=str(recorded.get("decision_id") or ""),
            tags=["worker_scheduler", decision, tier, risk],
        )
    except Exception:  # noqa: BLE001 — scheduler must not depend on registry writes
        logger.exception("could not trace scheduler lease decision for task=%s", task_id)


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
    target_run_id: str | None = None,
) -> list[dict[str, Any]]:
    """Promote Lead fan-out queued runs into Lane B without creating duplicate runs."""
    return dispatch_queued_lead_fan_out_runs(
        companies=companies,
        starts_bound=starts_bound,
        active_bound=active_bound,
        executing_run_count=_executing_run_count,
        employee_for_role=_employee_for_role,
        dispatch_worker_run=_dispatch_worker_run,
        target_run_id=target_run_id,
    )


def kick_lead_fan_out_dispatch(
    *,
    starts_bound: int = 3,
    target_run_id: str | None = None,
) -> list[dict[str, Any]]:
    """Start queued Lead fan-out runs even when continuous workers are paused.

    Operator Send / Lead decompose is an explicit handoff. Do not require
    autonomy Full (scheduler_enabled) — only capacity + worker_dispatch_enabled.
    """
    if not worker_dispatch_enabled():
        return []
    _configs, _defaults, companies, _staffing = load_workspace_agent_configs()
    active_bound = max_active_executing()
    executing = _executing_run_count()
    free_slots = max(0, active_bound - executing)
    if free_slots <= 0:
        return []
    try:
        bound = max(1, int(starts_bound))
    except (TypeError, ValueError):
        bound = 1
    bound = min(bound, free_slots)
    return _dispatch_queued_lead_fan_out_runs(
        companies=companies,
        starts_bound=bound,
        active_bound=active_bound,
        target_run_id=target_run_id,
    )


def run_observation_tick() -> dict[str, Any]:
    """Run always-on watcher housekeeping without starting worker shifts."""
    if not observation_scheduler_enabled():
        return {"enabled": False, "sources": {}}
    result: dict[str, Any] = {"enabled": True, "sources": {}}
    reaped = reap_stale_employee_runs()
    result["reaped_count"] = len(reaped)
    if reaped:
        logger.info("continuous worker tick reaped %s stale run(s)", len(reaped))

    # An operator composer thread has no employee_role, so the reaper above
    # deliberately skips it -- correctly, a real turn can run long. But that
    # left no periodic path back to a sane state for one actually abandoned
    # (tab closed mid-turn); only a control-plane restart could resolve it.
    reaped_interactive = reap_stale_interactive_runs()
    result["reaped_interactive_count"] = len(reaped_interactive)
    if reaped_interactive:
        logger.info(
            "continuous worker tick reaped %s abandoned interactive run(s)",
            len(reaped_interactive),
        )

    # Regression guard for a real outage: preserve_isolation keeps a checkout on
    # disk for operator recovery after a blocked/failed publish, but nothing
    # ever swept those checkouts afterward. 77 accumulated (7.9G) on this host's
    # 9.8G tmpfs /tmp and filled it to 100%, which then failed *every new*
    # isolation with "refusing to write the bound project root" -- a
    # platform-wide stall from disk pressure, not a code defect anywhere else.
    reaped_isolations = reap_abandoned_worker_isolations()
    result["reaped_isolation_count"] = len(reaped_isolations)
    if reaped_isolations:
        logger.info(
            "continuous worker tick reaped %s abandoned isolation checkout(s)",
            len(reaped_isolations),
        )

    missing_task_runs = reconcile_employee_runs_missing_tasks()
    result["missing_task_reconciled_count"] = len(missing_task_runs)
    if missing_task_runs:
        logger.info(
            "continuous worker tick cancelled %s active employee run(s) with missing tasks",
            len(missing_task_runs),
        )

    abandoned = reap_abandoned_review_ready_runs()
    result["abandoned_count"] = len(abandoned)
    if abandoned:
        logger.info(
            "continuous worker tick completed %s abandoned review_ready run(s)",
            len(abandoned),
        )

    pruned = prune_terminal_employee_runs()
    result["pruned_count"] = len(pruned)
    if pruned:
        logger.info("continuous worker tick pruned %s terminal employee run(s)", len(pruned))

    try:
        from app.workspace_delivery.poll import poll_pending_deliveries

        timed_out = poll_pending_deliveries()
        result["delivery_updates_count"] = len(timed_out)
        if timed_out:
            logger.info("workspace delivery poll updated %s delivery(ies)", len(timed_out))
    except Exception:  # noqa: BLE001 — never block scheduler on delivery poll
        logger.exception("workspace delivery poll failed")
        result["delivery_poll_error"] = True

    work_source_result: dict[str, Any] = {}
    try:
        from app.workspace_agents.company_work_sources import run_scheduled_work_sources

        work_source_result = run_scheduled_work_sources(observation_only=True)
        result["sources"] = work_source_result.get("sources") or {}
        recovered = work_source_result.get("recovered_leases") or []
        result["recovered_leases_count"] = len(recovered)
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
        result["work_sources_error"] = True
    return result


def run_continuous_worker_tick(
    *,
    starts_bound_override: int | None = None,
) -> list[dict[str, Any]]:
    """Run watcher observation, then start bounded role-tagged runs when enabled."""
    run_observation_tick()

    # Lead fan-out/decompose is an explicit operator handoff, not background
    # auto-leasing.  If the control plane restarts after Dana queued a
    # specialist run but before the one-shot dispatch kick succeeds, Manual/Semi
    # mode used to leave Priya/Marco/etc. stranded in queued forever.  Keep this
    # rescue before the scheduler_enabled gate so watcher ticks can self-heal
    # only those already-approved handoff runs without enabling general worker
    # autonomy.
    try:
        lead_fan_out_started = kick_lead_fan_out_dispatch(starts_bound=2)
        if lead_fan_out_started:
            logger.info(
                "continuous worker tick rescued %s queued Lead handoff run(s)",
                len(lead_fan_out_started),
            )
    except Exception:  # noqa: BLE001 — never block scheduler on handoff rescue
        logger.exception("queued Lead handoff rescue failed")

    # Semi / Manual pause continuous specialist leasing, but Lead-owned board
    # tickets and soft-failed handoff autostarts still need operator_start + kick.
    try:
        from app.workspace_agents.lead_board_pickup import pickup_open_lead_board_tasks

        lead_picked = pickup_open_lead_board_tasks(starts_bound=2)
        if lead_picked:
            logger.info(
                "continuous worker tick picked up %s open Lead ticket(s)",
                len(lead_picked),
            )
    except Exception:  # noqa: BLE001 — never block scheduler on Lead pickup
        logger.exception("lead board pickup failed")

    try:
        from app.workspace_agents.handoff_autostart_retry import (
            retry_pending_handoff_autostarts,
        )

        handoff_retried = retry_pending_handoff_autostarts(starts_bound=2)
        if handoff_retried:
            logger.info(
                "continuous worker tick retried %s handoff autostart(s)",
                len(handoff_retried),
            )
    except Exception:  # noqa: BLE001 — never block scheduler on handoff retry
        logger.exception("handoff autostart retry failed")

    if not scheduler_enabled():
        return []

    try:
        from app.workspace_agents.company_work_sources import run_scheduled_work_sources

        action_sources = run_scheduled_work_sources(action_only=True)
        action_created = (
            (action_sources.get("sources") or {}).get("file_size_patrol") or {}
        ).get("created_tasks") or []
        if action_created:
            logger.info(
                "continuous worker tick enqueued %s action-source task(s)",
                len(action_created),
            )
    except Exception:  # noqa: BLE001 — never block worker leasing on action sources
        logger.exception("scheduled company action sources failed")

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
            skip_reason = continuous_auto_start_skip_reason(workspace_id, role)
            if skip_reason:
                logger.info(
                    "continuous worker tick skipped role=%s workspace=%s: %s",
                    role,
                    workspace_id,
                    skip_reason,
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
                _trace_scheduler_lease_decision(
                    task=claimed,
                    decision="refuse",
                    tier=lease_decision.tier,
                    risk=lease_decision.risk,
                    explanation=lease_decision.reason,
                )
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
            _trace_scheduler_lease_decision(
                task=claimed,
                decision="dispatch",
                tier=lease_decision.tier,
                risk=lease_decision.risk,
                explanation=lease_decision.reason,
                run_id=str(record.get("run_id") or "").strip() or None,
            )
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
            await asyncio.to_thread(run_due_attention_scan_and_log)
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
