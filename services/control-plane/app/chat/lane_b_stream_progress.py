"""Throttled Lane B stream progress callbacks (stale-reaper receipts)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from app.chat.progress_milestones import persist_stream_delta
from app.runs.service import RunLifecycleError, RunNotFoundError, append_run_execution_receipt

_LANE_B_PROGRESS_RECEIPT_MIN_SECONDS = 60.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_lane_b_stream_on_chunk(
    *,
    thread_id: str,
    agent_message_id: str,
    dispatch_run_id: str,
) -> tuple[Callable[[str, str], None], Callable[[], str]]:
    """Return (on_chunk, get_milestone_content) for a Lane B stream job."""
    state: dict[str, Any] = {"milestone_content": "", "last_progress_at": 0.0}
    progress_lock = threading.Lock()

    def on_chunk(accumulated: str, delta: str) -> None:
        state["milestone_content"] = persist_stream_delta(
            thread_id=thread_id,
            message_id=agent_message_id,
            previous_content=str(state["milestone_content"] or ""),
            accumulated=accumulated,
            delta=delta,
            updated_at=_utc_now(),
        )
        run_id = str(dispatch_run_id or "").strip()
        if not run_id:
            return
        now = time.monotonic()
        with progress_lock:
            if now - float(state["last_progress_at"]) < _LANE_B_PROGRESS_RECEIPT_MIN_SECONDS:
                return
            state["last_progress_at"] = now
        try:
            append_run_execution_receipt(
                run_id,
                receipt_type="worker_progress",
                receipt_summary="IDE agent turn still executing",
                actor="cli_runtime",
            )
        except (RunLifecycleError, RunNotFoundError):
            return

    def get_milestone_content() -> str:
        return str(state["milestone_content"] or "")

    return on_chunk, get_milestone_content
