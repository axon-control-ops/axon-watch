"""Progress/heartbeat helpers for continuous worker dispatch."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from app.runs.service import RunLifecycleError, RunNotFoundError, append_run_execution_receipt
from app.workspace_agents.worker_ide_stream import WorkerIdeStream, stream_worker_chunk

logger = logging.getLogger(__name__)

HEARTBEAT_SECONDS = 60.0
PROGRESS_RECEIPT_MIN_SECONDS = 60.0


def throttled_worker_stream_progress(
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
                logger.exception("continuous worker IDE stream chunk failed for %s", run_id)
        now = time.monotonic()
        with lock:
            if now - last_at < PROGRESS_RECEIPT_MIN_SECONDS:
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


def run_dispatch_heartbeat(run_id: str, stop: threading.Event) -> None:
    """Record dispatch-thread liveness; stale reap ignores heartbeat-only bumps."""
    while not stop.wait(HEARTBEAT_SECONDS):
        try:
            append_run_execution_receipt(
                run_id,
                receipt_type="worker_heartbeat",
                receipt_summary="Continuous worker dispatch still running",
                actor="workspace_scheduler",
            )
        except (RunLifecycleError, RunNotFoundError):
            return
