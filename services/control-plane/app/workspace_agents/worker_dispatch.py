"""Headless Lane B dispatch for scheduled employee-agent runs."""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
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
from app.workspace_agents.worker_ide_stream import (
    WorkerIdeStream,
    fail_worker_ide_stream,
    finalize_worker_ide_stream,
    prepare_worker_ide_stream,
    stream_worker_chunk,
)
from app.workspace_agents.worker_isolation import (
    IsolationError,
    cleanup_worker_isolation,
    create_worker_isolation,
    isolation_receipt_summary,
    worker_agent_workspace,
)
from app.workspace_agents.worker_prompt import build_continuous_worker_prompt
from app.persistence import task_store

logger = logging.getLogger(__name__)

_HEARTBEAT_SECONDS = 60.0
_PROGRESS_RECEIPT_MIN_SECONDS = 60.0


def worker_dispatch_enabled() -> bool:
    raw = os.environ.get("AXON_WATCH_WORKER_SCHEDULER_DISPATCH", "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def _throttled_worker_stream_progress(
    run_id: str,
    ide_stream: WorkerIdeStream | None = None,
) -> Callable[[str, str], None]:
    """Emit worker_progress receipts and mirror chunks into the employee IDE thread."""
    last_at = 0.0
    lock = threading.Lock()
    milestone_content = ""

    def on_chunk(accumulated: str, delta: str) -> None:
        nonlocal last_at, milestone_content
        if ide_stream is not None:
            try:
                milestone_content = stream_worker_chunk(
                    ide_stream,
                    previous_content=milestone_content,
                    accumulated=accumulated,
                    delta=delta,
                )
            except Exception:  # noqa: BLE001 — never block dispatch on UI mirror
                logger.exception(
                    "continuous worker IDE stream chunk failed for %s",
                    run_id,
                )
        now = time.monotonic()
        with lock:
            if now - last_at < _PROGRESS_RECEIPT_MIN_SECONDS:
                return
            last_at = now
        try:
            append_run_execution_receipt(
                run_id,
                receipt_type="worker_progress",
                receipt_summary="Continuous worker dispatch still executing",
                actor="workspace_scheduler",
            )
        except (RunLifecycleError, RunNotFoundError):
            return

    return on_chunk


def _run_dispatch_heartbeat(run_id: str, stop: threading.Event) -> None:
    """Record dispatch-thread liveness; stale reap ignores heartbeat-only bumps."""
    while not stop.wait(_HEARTBEAT_SECONDS):
        try:
            append_run_execution_receipt(
                run_id,
                receipt_type="worker_heartbeat",
                receipt_summary="Continuous worker dispatch still running",
                actor="workspace_scheduler",
            )
        except (RunLifecycleError, RunNotFoundError):
            return


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
        target=_run_dispatch_heartbeat,
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
        heartbeat.start()
        isolation_root = create_worker_isolation(workspace_id=workspace_id, run_id=run_id)
        agent_root = worker_agent_workspace(isolation_root)
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
        lane_b_result = generate_lane_b_result(
            context=context,
            user_prompt=prompt,
            run_id=run_id,
            execution_access="full",
            on_chunk=_throttled_worker_stream_progress(run_id, ide_stream),
            cursor_trust_policy="worker",
            workspace_root=agent_root,
        )
        reply_text = str(lane_b_result.get("content") or "")
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
                from app.workspace_agents.verifier_contract import (
                    has_passing_acceptance_evidence,
                    run_requires_acceptance_evidence,
                )
                from app.runs.service import get_run
                from app.workspace_delivery import publish_worker_isolation

                run_snapshot = get_run(run_id)
                if run_requires_acceptance_evidence(run_snapshot) and not has_passing_acceptance_evidence(
                    run_id
                ):
                    finalized = _fail_worker_run(
                        run_id,
                        receipt_summary=(
                            "Workspace delivery blocked: missing or failing "
                            "acceptance_evidence (Gate 6)"
                        ),
                    )
                    dispatched = False
                    preserve_isolation = True
                else:
                    publish = publish_worker_isolation(
                        workspace_id=workspace_id,
                        run_id=run_id,
                        isolation_root=agent_root,
                        task_id=task_id,
                        turn_subject=str(task.get("goal") or "") if isinstance(task, dict) else None,
                    )
                    preserve_isolation = not publish.cleanup_isolation
                    if publish.ok:
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
                    task_store.complete_task(task_id, run_id=run_id)
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
