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
    fail_run,
    touch_run_activity,
)
from app.terminal.session_registry import ensure_agent_session
from app.workspace_agents.config_loader import EmployeeConfig
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


def _throttled_worker_stream_progress(run_id: str) -> Callable[[str, str], None]:
    """Emit worker_progress receipts from Lane B stream chunks (stale TTL uses these)."""
    last_at = 0.0
    lock = threading.Lock()

    def on_chunk(_accumulated: str, _delta: str) -> None:
        nonlocal last_at
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
        # #region agent log
        try:
            import json as _json
            import time as _time
            from pathlib import Path as _Path

            _payload = {
                "sessionId": "fc0b35",
                "runId": "pre-fix",
                "hypothesisId": "H2",
                "location": "worker_dispatch.py:dispatch_continuous_worker_run",
                "message": "dispatch refused missing leased task",
                "data": {
                    "run_id": run_id,
                    "task_id": task_id or None,
                    "task_status": (task or {}).get("status") if task else None,
                    "task_store_file": getattr(task_store, "__file__", None),
                },
                "timestamp": int(_time.time() * 1000),
            }
            with _Path(
                "/home/edp/axon-nvme/repos/axon-watch/.cursor/debug-fc0b35.log"
            ).open("a", encoding="utf-8") as _fh:
                _fh.write(_json.dumps(_payload) + "\n")
        except Exception:
            pass
        # #endregion
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
            on_chunk=_throttled_worker_stream_progress(run_id),
            cursor_trust_policy="worker",
            workspace_root=agent_root,
        )
        dispatched, finalized = finalize_lane_b_agent_run(
            dispatch_run_id=run_id,
            lane_b_result=lane_b_result,
            reply_text=str(lane_b_result.get("content") or ""),
        )
        if dispatched and finalized is not None:
            phase = str(finalized.get("phase") or "").strip().lower()
            try:
                if phase == "completed":
                    task_store.complete_task(task_id, run_id=run_id)
                elif phase == "failed":
                    task_store.fail_task(task_id, run_id=run_id)
            except task_store.TaskLedgerError:
                logger.exception("task ledger finalize failed for %s task=%s", run_id, task_id)
    except IsolationError as exc:
        logger.exception(
            "continuous worker isolation failed for %s role=%s",
            run_id,
            employee.role,
        )
        failed = _fail_worker_run(
            run_id,
            receipt_summary=f"Continuous worker isolation failed: {exc}",
        )
        try:
            task_store.fail_task(task_id, run_id=run_id)
        except task_store.TaskLedgerError:
            logger.exception("task fail after isolation error for %s", task_id)
        return False, failed
    except Exception as exc:  # noqa: BLE001 — never leave role-tagged runs stuck executing
        logger.exception(
            "continuous worker dispatch crashed for %s role=%s",
            run_id,
            employee.role,
        )
        failed = _fail_worker_run(
            run_id,
            receipt_summary=f"Continuous worker dispatch failed: {exc}",
        )
        try:
            task_store.fail_task(task_id, run_id=run_id)
        except task_store.TaskLedgerError:
            logger.exception("task fail after dispatch crash for %s", task_id)
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
