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
from app.workspace_agents.worker_prompt import build_continuous_worker_prompt

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

    stop_heartbeat = threading.Event()
    heartbeat = threading.Thread(
        target=_run_dispatch_heartbeat,
        args=(run_id, stop_heartbeat),
        daemon=True,
        name=f"worker-heartbeat-{run_id}",
    )
    try:
        touch_run_activity(run_id)
        append_run_execution_receipt(
            run_id,
            receipt_type="worker_dispatch_started",
            receipt_summary=f"Continuous worker dispatch started for role={employee.role}",
            actor="workspace_scheduler",
        )
        heartbeat.start()
        prompt = build_continuous_worker_prompt(workspace_id=workspace_id, employee=employee)
        ensure_agent_session(workspace_id=workspace_id, run_id=run_id)
        context = LaneBContext(workspace_id=workspace_id, composer_mode="agent")
        lane_b_result = generate_lane_b_result(
            context=context,
            user_prompt=prompt,
            run_id=run_id,
            execution_access="full",
            on_chunk=_throttled_worker_stream_progress(run_id),
        )
        dispatched, finalized = finalize_lane_b_agent_run(
            dispatch_run_id=run_id,
            lane_b_result=lane_b_result,
            reply_text=str(lane_b_result.get("content") or ""),
        )
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
        return False, failed
    finally:
        stop_heartbeat.set()
        heartbeat.join(timeout=2.0)

    if not dispatched:
        logger.warning(
            "continuous worker dispatch fallback for %s role=%s: %s",
            run_id,
            employee.role,
            lane_b_result.get("reason") or lane_b_result.get("content"),
        )
    return dispatched, finalized
