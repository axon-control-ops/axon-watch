"""Lifecycle watcher for Axon agent terminal jobs.

Every job is wrapped in a job-scoped exit sentinel and watched, so status,
exit code, and captured output always resolve — with or without a chat stream
to tee into. A job that never finishes is interrupted at its own deadline
rather than pinning the owning run until the run-level stale timeout.
"""

from __future__ import annotations

import re
import shlex
import threading
import time
from typing import Any

from app.cli_runtime.stream_blocks.terminal_blocks import render_axon_job_terminal_fence
from app.terminal.agent_job_chat import (
    append_live_job_fence_body,
    close_live_job_fence,
    register_live_job_fence,
)
from app.terminal.agent_job_registry import (
    append_job_output_tail,
    mark_job_finished,
    release_job_watcher,
    store_job_watcher,
    utc_now,
)

_STREAM_FLUSH_SECONDS = 0.15
# Keep ordinary job deadlines under the 720s worker-run stale cutoff so a hung
# command fails its own job with a readable receipt instead of stalling the run.
DEFAULT_JOB_TIMEOUT_SECONDS = 600.0
# OTA / EAS / Expo / Vercel ship jobs routinely run past ten minutes and are the
# reason this helper exists — they must not inherit the short worker deadline.
SHIP_JOB_TIMEOUT_SECONDS = 3600.0
MAX_JOB_TIMEOUT_SECONDS = 3600.0


def default_timeout_for_command(command: str) -> float:
    from app.cli_runtime.long_running_shell import is_long_running_ship_shell

    if is_long_running_ship_shell(command):
        return SHIP_JOB_TIMEOUT_SECONDS
    return DEFAULT_JOB_TIMEOUT_SECONDS


def exit_sentinel_re(job_id: str) -> re.Pattern[str]:
    """Job-scoped sentinel so concurrent jobs on the shared PTY never cross-talk."""
    return re.compile(rf"__AXON_JOB_EXIT:{re.escape(job_id)}:(-?\d+)__")


def wrap_with_exit_sentinel(command: str, job_id: str) -> str:
    """Run command in a subshell and print a parseable, job-scoped exit marker."""
    # Prefer bash -c with shell-safe quoting over eval (handles pipes/quotes better).
    quoted = shlex.quote(command)
    return f"bash -c {quoted}; printf '\\n__AXON_JOB_EXIT:{job_id}:%s__\\n' \"$?\""


def resolve_timeout_seconds(value: float | int | None, *, command: str = "") -> float:
    """Explicit override wins; otherwise the deadline follows the command class."""
    fallback = default_timeout_for_command(command)
    if value is None:
        return fallback
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return fallback
    if seconds <= 0:
        return fallback
    return min(seconds, MAX_JOB_TIMEOUT_SECONDS)


def _flush_fence_to_chat(
    *,
    thread_id: str,
    message_id: str,
    job_id: str,
    command: str,
    body: str,
    closed: bool,
    exit_code: int | None,
) -> None:
    from app.chat.progress_milestones import persist_stream_delta
    from app.cli_runtime.stream_blocks.terminal_blocks import upsert_axon_job_terminal_fence
    from app.persistence import chat_store
    from app.terminal.agent_job_chat import merge_active_agent_job_terminals

    existing = chat_store.get_message(message_id)
    previous = str((existing or {}).get("content") or "")
    fence = render_axon_job_terminal_fence(
        command=command,
        job_id=job_id,
        body=body,
        closed=closed,
        exit_code=exit_code,
    )
    accumulated = upsert_axon_job_terminal_fence(previous, fence, job_id=job_id)
    accumulated = merge_active_agent_job_terminals(message_id, accumulated)
    persist_stream_delta(
        thread_id=thread_id,
        message_id=message_id,
        previous_content=previous,
        accumulated=accumulated,
        delta=fence,
        updated_at=utc_now(),
    )


def start_job_watcher(
    *,
    job_id: str,
    command: str,
    runtime: Any,
    chat_target: tuple[str, str] | None,
    timeout_seconds: float,
) -> None:
    """Track one job to a terminal state, optionally teeing output into chat.

    Lifecycle tracking is unconditional: without it a job with no resolvable
    chat target stayed ``running`` with an empty tail forever, which reads
    downstream as "verification jobs incomplete" and fails the run.
    """
    thread_id = chat_target[0] if chat_target is not None else ""
    message_id = chat_target[1] if chat_target is not None else ""
    sentinel_re = exit_sentinel_re(job_id)
    # Hold back at least a full sentinel so a split chunk is never missed.
    hold_back = len(f"__AXON_JOB_EXIT:{job_id}:") + 16

    if chat_target is not None:
        register_live_job_fence(job_id=job_id, message_id=message_id, command=command)
        _flush_fence_to_chat(
            thread_id=thread_id,
            message_id=message_id,
            job_id=job_id,
            command=command,
            body="",
            closed=False,
            exit_code=None,
        )

    buffer = ""
    last_flush = 0.0
    state_lock = threading.Lock()
    finished = False

    def _maybe_flush(*, force: bool = False) -> None:
        nonlocal last_flush
        if chat_target is None:
            return
        now = time.monotonic()
        if not force and (now - last_flush) < _STREAM_FLUSH_SECONDS:
            return
        from app.terminal.agent_job_chat import list_live_job_fences

        current = next(
            (item for item in list_live_job_fences(message_id) if item.job_id == job_id),
            None,
        )
        if current is None:
            return
        last_flush = now
        _flush_fence_to_chat(
            thread_id=thread_id,
            message_id=message_id,
            job_id=job_id,
            command=command,
            body=current.body,
            closed=current.closed,
            exit_code=current.exit_code,
        )

    def _emit(text: str) -> None:
        """Record output on the job record, and mirror to chat when streaming."""
        if not text:
            return
        if chat_target is not None:
            append_live_job_fence_body(job_id, message_id, text)
        append_job_output_tail(job_id, text)

    def _finish(*, status: str, exit_code: int | None, note: str = "") -> None:
        nonlocal buffer, finished
        with state_lock:
            if finished:
                return
            finished = True
            pending, buffer = buffer, ""
            _emit(pending)
            if note:
                _emit(f"\n[axon] {note}\n")
            if chat_target is not None:
                closed = close_live_job_fence(job_id, message_id, exit_code=exit_code)
                _flush_fence_to_chat(
                    thread_id=thread_id,
                    message_id=message_id,
                    job_id=job_id,
                    command=command,
                    body=closed.body if closed is not None else pending,
                    closed=True,
                    exit_code=exit_code,
                )
            mark_job_finished(job_id, status=status, exit_code=exit_code, note=note)
        release_job_watcher(job_id)
        if chat_target is not None:
            from app.chat.chat_stream_defer import release_deferred_chat_stream_if_idle

            release_deferred_chat_stream_if_idle(message_id)

    def on_output(chunk: bytes) -> None:
        nonlocal buffer
        if finished or not chunk:
            return
        text = chunk.decode("utf-8", errors="replace")
        with state_lock:
            if finished:
                return
            buffer += text
            match = sentinel_re.search(buffer)
            if match is None:
                # Stream visible text; keep incomplete sentinel fragments buffered.
                hold = min(len(buffer), hold_back)
                visible, buffer = buffer[: len(buffer) - hold], buffer[len(buffer) - hold :]
                if visible:
                    _emit(visible)
                    _maybe_flush()
                return
            exit_code = int(match.group(1))
            _emit(buffer[: match.start()])
            buffer = ""
        _finish(status="completed" if exit_code == 0 else "failed", exit_code=exit_code)

    def on_closed() -> None:
        # The PTY died before the sentinel arrived: the command's own result is
        # unknown, so do not report success it never claimed.
        _finish(
            status="failed",
            exit_code=None,
            note="terminal session closed before the job reported an exit code",
        )

    def _interrupt(*, status: str, note: str) -> None:
        """Interrupt the foreground command, then close the job out."""
        with state_lock:
            # Never SIGINT after this job ended — the PTY is shared, so a late
            # timer would interrupt whatever job is running now.
            if finished:
                return
        try:
            runtime.pty.write(b"\x03")
        except Exception:  # noqa: BLE001 - PTY may already be gone
            pass
        _finish(status=status, exit_code=None, note=note)

    unsubscribe = runtime.pty.subscribe(on_output, on_closed)
    timer = threading.Timer(
        timeout_seconds,
        lambda: _interrupt(
            status="timed_out",
            note=f"job exceeded its {int(timeout_seconds)}s deadline; sent SIGINT",
        ),
    )
    timer.daemon = True
    store_job_watcher(job_id, unsubscribe=unsubscribe, timer=timer, interrupt=_interrupt)
    timer.start()


__all__ = [
    "DEFAULT_JOB_TIMEOUT_SECONDS",
    "MAX_JOB_TIMEOUT_SECONDS",
    "exit_sentinel_re",
    "resolve_timeout_seconds",
    "start_job_watcher",
    "wrap_with_exit_sentinel",
]
