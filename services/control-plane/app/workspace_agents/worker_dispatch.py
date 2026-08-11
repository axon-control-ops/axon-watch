"""Headless Lane B dispatch for scheduled employee-agent runs."""

from __future__ import annotations

import logging
import os
import threading
from typing import Any

from app.chat.lane_b_agent import LaneBContext, generate_lane_b_result
from app.chat.lane_b_stream_execute import finalize_lane_b_agent_run
from app.runs.service import (
    RunLifecycleError,
    RunNotFoundError,
    append_run_execution_receipt,
    complete_run,
    fail_run,
    touch_run_activity,
)
from app.terminal.session_registry import ensure_agent_session
from app.workspace_agents.config_loader import EmployeeConfig
from app.workspace_agents.execution_policy_runtime import record_execution_policy_receipt, resolve_worker_execution_policy
from app.workspace_agents.worker_ide_stream import (
    WorkerIdeStream,
    fail_worker_ide_stream,
    finalize_worker_ide_stream,
    prepare_worker_ide_stream,
)
from app.workspace_agents.worker_isolation import (
    IsolationError,
    cleanup_worker_isolation,
    create_worker_isolation,
    isolation_receipt_summary,
    worker_agent_workspace,
)
from app.workspace_agents.worker_prompt import build_continuous_worker_prompt
from app.workspace_agents.worker_prompt import parse_out_of_scope_guard
from app.persistence import task_store
from app.persistence import worker_scheduler_settings_store
from app.workspace_agents.ask_autopilot import escalate_unresolved_operator_ask, maybe_resolve_safe_ask
from app.persistence.workspace_composer_prefs_store import (
    resolve_worker_runtime_model,
    resolve_worker_runtime_target,
)
from app.workspace_agents.worker_dispatch_progress import (
    run_dispatch_heartbeat,
    throttled_worker_stream_progress,
)
from app.workspace_agents.ops_delivery import (
    complete_ops_no_change_delivery,
    no_change_delivery_is_successful_ops_task,
)

logger = logging.getLogger(__name__)


def worker_dispatch_enabled() -> bool:
    raw = os.environ.get("AXON_WATCH_WORKER_SCHEDULER_DISPATCH", "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def _fail_worker_run(run_id: str, *, receipt_summary: str) -> dict[str, Any] | None:
    try:
        return fail_run(
            run_id,
            receipt_summary=receipt_summary,
            actor="workspace_scheduler",
        )
    except (RunLifecycleError, RunNotFoundError):
        logger.exception("continuous worker fail_run unavailable for %s", run_id)
        return None


def dispatch_continuous_worker_run(
    *,
    workspace_id: str,
    employee: EmployeeConfig,
    run_record: dict[str, Any],
) -> tuple[bool, dict[str, Any] | None]:
    """Run one bounded Lane B shift for a role-tagged worker run."""
    run_id = str(run_record.get("run_id") or "").strip()
    if not run_id:
        return False, None

    task_id = str(run_record.get("task_id") or "").strip()
    task = task_store.get_task(task_id) if task_id else None
    if task is None or str(task.get("status") or "").strip().lower() != "leased":
        failed = _fail_worker_run(
            run_id,
            receipt_summary=(
                "Continuous worker dispatch refused: missing leased task_id "
                f"(task_id={task_id or 'none'})"
            ),
        )
        return False, failed

    stop_heartbeat = threading.Event()
    heartbeat = threading.Thread(
        target=run_dispatch_heartbeat,
        args=(run_id, stop_heartbeat),
        daemon=True,
        name=f"worker-heartbeat-{run_id}",
    )
    isolation_root = None
    lane_b_result: dict[str, Any] = {}
    ide_stream: WorkerIdeStream | None = None
    dispatched = False
    finalized: dict[str, Any] | None = None
    try:
        touch_run_activity(run_id)
        try:
            task_store.renew_lease(
                task_id,
                lease_holder=str(task.get("lease_holder") or "").strip()
                or f"employee-{workspace_id}-{employee.role}",
            )
        except task_store.TaskLedgerError as exc:
            failed = _fail_worker_run(
                run_id,
                receipt_summary=f"Continuous worker lease renew failed: {exc}",
            )
            return False, failed
        append_run_execution_receipt(
            run_id,
            receipt_type="worker_dispatch_started",
            receipt_summary=(
                f"Continuous worker dispatch started for role={employee.role} "
                f"task={task_id}"
            ),
            actor="workspace_scheduler",
        )
        heartbeat.start()
        try:
            ide_stream = prepare_worker_ide_stream(
                workspace_id=workspace_id,
                employee=employee,
                run_id=run_id,
                task_id=task_id,
                task=task,
            )
            if ide_stream is None:
                logger.warning(
                    "continuous worker IDE stream prepare returned None for %s "
                    "role=%s (employee_id unresolved — specialist dock will stay empty)",
                    run_id,
                    employee.role,
                )
        except Exception:  # noqa: BLE001 — dispatch must continue even if IDE mirror fails
            logger.exception(
                "continuous worker IDE stream prepare failed for %s role=%s",
                run_id,
                employee.role,
            )
            ide_stream = None
        isolation_root = create_worker_isolation(workspace_id=workspace_id, run_id=run_id)
        agent_root = worker_agent_workspace(isolation_root)
        execution_policy = resolve_worker_execution_policy(
            employee=employee, task_payload=task, workspace_root=agent_root
        )
        record_execution_policy_receipt(run_id, execution_policy)
        append_run_execution_receipt(
            run_id,
            receipt_type="worker_isolation_created",
            receipt_summary=isolation_receipt_summary(isolation_root),
            actor="workspace_scheduler",
            success=True,
            intent="worker_isolation",
        )
        prompt = build_continuous_worker_prompt(
            workspace_id=workspace_id,
            employee=employee,
            task=task,
        )
        ensure_agent_session(workspace_id=workspace_id, run_id=run_id)
        context = LaneBContext(workspace_id=workspace_id, composer_mode="agent")
        # Honor the operator's Agent Dock runtime-target pick — without this,
        # continuous workers silently ignore it and fall back to the server's
        # default runtime regardless of what's selected in the composer.
        runtime_target = resolve_worker_runtime_target(workspace_id)
        runtime_family = (runtime_target or "cursor_local").split("_", 1)[0]
        runtime_model = resolve_worker_runtime_model(workspace_id, runtime_family)
        lane_b_result = generate_lane_b_result(
            context=context,
            user_prompt=prompt,
            run_id=run_id,
            runtime_target=runtime_target,
            runtime_model=runtime_model,
            execution_access=execution_policy.execution_access,
            on_chunk=throttled_worker_stream_progress(run_id, ide_stream),
            cursor_trust_policy=execution_policy.trust_policy,
            workspace_root=agent_root,
            execution_policy=execution_policy,
            allow_git_dispatch=False,
        )
        reply_text = str(lane_b_result.get("content") or "")
        from app.workspace_agents.employee_first_person import (
            rewrite_employee_third_person_to_first,
        )

        reply_text = rewrite_employee_third_person_to_first(
            reply_text,
            str(employee.name or "").strip() or None,
        )
        auto_ask_resolution = maybe_resolve_safe_ask(
            reply_text,
            auto_mode_enabled=bool(
                worker_scheduler_settings_store.load_settings().get("scheduler_enabled")
            ),
        )
        if auto_ask_resolution is not None:
            append_run_execution_receipt(
                run_id,
                receipt_type="auto_ask_resolution",
                receipt_summary=auto_ask_resolution.receipt_summary,
                actor="workspace_scheduler",
                success=True,
                intent="worker_autonomy",
            )
        escalate_unresolved_operator_ask(
            reply_text,
            employee_name=employee.name,
            employee_role=str(employee.role or ""),
            workspace_id=workspace_id,
            task_id=task_id,
            run_id=run_id,
        )
        scope_guard_detail = parse_out_of_scope_guard(reply_text)
        if scope_guard_detail:
            dispatched = False
            finalized = _fail_worker_run(
                run_id,
                receipt_summary=(
                    "Continuous worker scope guard tripped: "
                    f"{scope_guard_detail}"
                ),
            )
        else:
            dispatched, finalized = finalize_lane_b_agent_run(
                dispatch_run_id=run_id,
                lane_b_result=lane_b_result,
                reply_text=reply_text,
                workspace_root=str(agent_root),
                defer_complete=True,
            )
        preserve_isolation = False
        if dispatched and finalized is not None:
            phase = str(finalized.get("phase") or "").strip().lower()
            if phase not in {"failed", "cancelled"}:
                from app.workspace_agents.completion_gate import run_worker_delivery_gate

                gate = run_worker_delivery_gate(
                    workspace_id=workspace_id,
                    run_id=run_id,
                    task_id=task_id,
                    task=task,
                    isolation_root=agent_root,
                    reply_text=reply_text,
                )
                if not gate.passed:
                    finalized = _fail_worker_run(
                        run_id,
                        receipt_summary=gate.reason,
                    )
                    dispatched = False
                    preserve_isolation = gate.preserve_isolation
                    publish = None
                else:
                    publish = gate.publish
                if not dispatched or publish is None:
                    pass
                else:
                    preserve_isolation = not publish.cleanup_isolation
                    if (
                        publish.ok
                        and publish.stage == "no_change"
                        and publish.delivery is not None
                        and execution_policy.execution_access == "full"
                    ):
                        if no_change_delivery_is_successful_ops_task(task):
                            finalized = complete_ops_no_change_delivery(
                                run_id,
                                fail_worker_run=lambda summary: _fail_worker_run(
                                    run_id,
                                    receipt_summary=summary,
                                ),
                            )
                            dispatched = (
                                finalized is not None
                                and finalized.get("phase") == "completed"
                            )
                        elif auto_ask_resolution is not None:
                            finalized = _fail_worker_run(
                                run_id,
                                receipt_summary=(
                                    auto_ask_resolution.receipt_summary
                                    + ". Reopening the task so the next Auto shift "
                                    "continues with that selected answer."
                                ),
                            )
                            dispatched = False
                        else:
                            finalized = _fail_worker_run(
                                run_id,
                                receipt_summary=(
                                    "Workspace delivery blocked: full-access worker produced "
                                    f"no publishable changes ({publish.detail})"
                                )
                            )
                            dispatched = False
                    elif (
                        auto_ask_resolution is not None
                        and publish.ok
                        and publish.stage == "no_change"
                    ):
                        finalized = _fail_worker_run(
                            run_id,
                            receipt_summary=(
                                auto_ask_resolution.receipt_summary
                                + ". Reopening the task so the next Auto shift continues "
                                "with that selected answer."
                            ),
                        )
                        dispatched = False
                    elif publish.ok:
                        try:
                            finalized = complete_run(run_id)
                        except RunLifecycleError as exc:
                            logger.exception("complete_run after delivery failed for %s", run_id)
                            finalized = _fail_worker_run(
                                run_id,
                                receipt_summary=f"Delivery succeeded but complete_run failed: {exc}",
                            )
                            dispatched = False
                    else:
                        finalized = _fail_worker_run(
                            run_id,
                            receipt_summary=(
                                f"Workspace delivery blocked at {publish.stage}: {publish.detail}"
                            ),
                        )
                        dispatched = False
        if ide_stream is not None:
            try:
                finalize_worker_ide_stream(
                    ide_stream,
                    reply_text=reply_text,
                    dispatched=dispatched,
                    run_record=finalized,
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "continuous worker IDE stream finalize failed for %s",
                    run_id,
                )
            ide_stream = None
        if finalized is not None:
            phase = str(finalized.get("phase") or "").strip().lower()
            try:
                if phase == "completed":
                    completed = task_store.complete_task(task_id, run_id=run_id)
                    try:
                        from app.workspace_agents.task_duplicate_cleanup import (
                            cleanup_after_task_completed,
                        )

                        cleanup_after_task_completed(completed)
                    except Exception:  # noqa: BLE001
                        logger.exception(
                            "waiting duplicate cleanup failed for %s task=%s",
                            run_id,
                            task_id,
                        )
                elif phase == "failed":
                    task_store.fail_task(task_id, run_id=run_id)
            except task_store.TaskLedgerError:
                logger.exception("task ledger finalize failed for %s task=%s", run_id, task_id)
            if phase in {"completed", "failed"}:
                try:
                    from app.workspace_agents.lead_replan import notify_lead_after_worker_task

                    notify_lead_after_worker_task(
                        workspace_id=workspace_id,
                        task_id=task_id,
                        run_id=run_id,
                        employee_role=str(employee.role or ""),
                        employee_name=str(employee.name or ""),
                        phase=phase,
                        reply_text=reply_text,
                    )
                except Exception:  # noqa: BLE001 — never block worker finalize on Lead notify
                    logger.exception(
                        "lead notify/synthesize after worker task failed for %s task=%s",
                        run_id,
                        task_id,
                    )
        if preserve_isolation:
            # Keep disposable checkout for operator recovery after publish failure.
            isolation_root = None
    except IsolationError as exc:
        logger.exception(
            "continuous worker isolation failed for %s role=%s",
            run_id,
            employee.role,
        )
        if ide_stream is not None:
            try:
                fail_worker_ide_stream(
                    ide_stream,
                    error=f"Continuous worker isolation failed: {exc}",
                    run_id=run_id,
                )
            except Exception:  # noqa: BLE001
                logger.exception("continuous worker IDE stream fail failed for %s", run_id)
            ide_stream = None
        failed = _fail_worker_run(
            run_id,
            receipt_summary=f"Continuous worker isolation failed: {exc}",
        )
        try:
            task_store.fail_task(task_id, run_id=run_id)
        except task_store.TaskLedgerError:
            logger.exception("task fail after isolation error for %s", task_id)
        try:
            from app.workspace_agents.lead_replan import notify_lead_after_worker_task

            notify_lead_after_worker_task(
                workspace_id=workspace_id,
                task_id=task_id,
                run_id=run_id,
                employee_role=str(employee.role or ""),
                employee_name=str(employee.name or ""),
                phase="failed",
                reply_text=str(exc),
            )
        except Exception:  # noqa: BLE001
            logger.exception("lead notify after isolation fail for %s", run_id)
        return False, failed
    except Exception as exc:  # noqa: BLE001 — never leave role-tagged runs stuck executing
        logger.exception(
            "continuous worker dispatch crashed for %s role=%s",
            run_id,
            employee.role,
        )
        if ide_stream is not None:
            try:
                fail_worker_ide_stream(
                    ide_stream,
                    error=f"Continuous worker dispatch failed: {exc}",
                    run_id=run_id,
                )
            except Exception:  # noqa: BLE001
                logger.exception("continuous worker IDE stream fail failed for %s", run_id)
            ide_stream = None
        failed = _fail_worker_run(
            run_id,
            receipt_summary=f"Continuous worker dispatch failed: {exc}",
        )
        try:
            task_store.fail_task(task_id, run_id=run_id)
        except task_store.TaskLedgerError:
            logger.exception("task fail after dispatch crash for %s", task_id)
        try:
            from app.workspace_agents.lead_replan import notify_lead_after_worker_task

            notify_lead_after_worker_task(
                workspace_id=workspace_id,
                task_id=task_id,
                run_id=run_id,
                employee_role=str(employee.role or ""),
                employee_name=str(employee.name or ""),
                phase="failed",
                reply_text=str(exc),
            )
        except Exception:  # noqa: BLE001
            logger.exception("lead notify after dispatch crash for %s", run_id)
        return False, failed
    finally:
        stop_heartbeat.set()
        heartbeat.join(timeout=2.0)
        if isolation_root is not None:
            cleanup = cleanup_worker_isolation(isolation_root)
            try:
                append_run_execution_receipt(
                    run_id,
                    receipt_type="worker_isolation_cleanup",
                    receipt_summary=(
                        f"worker isolation cleanup removed={cleanup.get('removed')} "
                        f"cleaned={cleanup.get('cleaned')}"
                    ),
                    actor="workspace_scheduler",
                    success=bool(cleanup.get("cleaned")),
                    intent="worker_isolation",
                )
            except (RunLifecycleError, RunNotFoundError):
                logger.exception("worker isolation cleanup receipt failed for %s", run_id)

    if not dispatched:
        logger.warning(
            "continuous worker dispatch fallback for %s role=%s: %s",
            run_id,
            employee.role,
            lane_b_result.get("reason") or lane_b_result.get("content"),
        )
    return dispatched, finalized
