"""Axon-owned agent-terminal jobs (not Cursor shellToolCall detach).

Enqueue a command into the persistent agent PTY so the operator can watch live
logs in the vaxon tab. Optional ``stream_to_chat`` tees PTY output into an open
``:::terminal`` fence on the active assistant message.
"""

from __future__ import annotations

import re
import threading
import time
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.cli_runtime.long_running_shell import is_long_running_ship_shell
from app.cli_runtime.stream_blocks.terminal_blocks import render_axon_job_terminal_fence
from app.terminal.active_chat_stream import get_active_chat_stream
from app.terminal.agent_job_chat import (
    append_live_job_fence_body,
    close_live_job_fence,
    register_live_job_fence,
    reset_live_job_fences,
)
from app.terminal.session_registry import ensure_agent_session, serialize_session
from app.terminal.session_runtime import ensure_runtime
from app.terminal.ship_command_guards import assert_ship_command_allowed
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root

_MAX_COMMAND_CHARS = 32_768
_EXIT_SENTINEL_RE = re.compile(r"__AXON_JOB_EXIT:(-?\d+)__")
_STREAM_FLUSH_SECONDS = 0.15
_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}
_tee_unsubscribers: dict[str, Any] = {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _agent_command_bytes(value: object) -> bytes | None:
    if not isinstance(value, str):
        return None
    command = value.strip()
    if not command or len(command) > _MAX_COMMAND_CHARS or "\x00" in command:
        return None
    return f"{command}\n".encode("utf-8")


def _wrap_with_exit_sentinel(command: str) -> str:
    """Run command in a subshell and print a parseable exit marker."""
    import shlex

    # Prefer bash -c with shell-safe quoting over eval (handles pipes/quotes better).
    quoted = shlex.quote(command)
    return f"bash -c {quoted}; printf '\\n__AXON_JOB_EXIT:%s__\\n' \"$?\""


def _resolve_stream_target(
    *,
    workspace_id: str,
    thread_id: str | None,
    message_id: str | None,
) -> tuple[str, str] | None:
    clean_thread = str(thread_id or "").strip()
    clean_message = str(message_id or "").strip()
    if clean_thread and clean_message:
        return clean_thread, clean_message
    active = get_active_chat_stream(workspace_id)
    if active is None:
        return None
    return active.thread_id, active.message_id


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
    from app.cli_runtime.stream_blocks.terminal_blocks import upsert_axon_job_terminal_fence

    accumulated = upsert_axon_job_terminal_fence(previous, fence, job_id=job_id)
    accumulated = merge_active_agent_job_terminals(message_id, accumulated)
    persist_stream_delta(
        thread_id=thread_id,
        message_id=message_id,
        previous_content=previous,
        accumulated=accumulated,
        delta=fence,
        updated_at=_utc_now(),
    )


def _start_chat_tee(
    *,
    job_id: str,
    workspace_id: str,
    command: str,
    thread_id: str,
    message_id: str,
    runtime: Any,
) -> None:
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

    def _decode(chunk: bytes) -> str:
        return chunk.decode("utf-8", errors="replace")

    def _maybe_flush(*, force: bool = False) -> None:
        nonlocal last_flush
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

    def on_output(chunk: bytes) -> None:
        nonlocal buffer, finished
        if finished or not chunk:
            return
        text = _decode(chunk)
        with state_lock:
            buffer += text
            match = _EXIT_SENTINEL_RE.search(buffer)
            if match is None:
                # Stream visible text; keep incomplete sentinel fragments buffered.
                safe = buffer
                # Hold back a short tail that might be a partial sentinel.
                hold = min(len(safe), 32)
                visible, buffer = safe[:-hold], safe[-hold:]
                if visible:
                    append_live_job_fence_body(job_id, message_id, visible)
                    _maybe_flush()
                return

            before = buffer[: match.start()]
            exit_code = int(match.group(1))
            buffer = buffer[match.end() :]
            if before:
                append_live_job_fence_body(job_id, message_id, before)
            closed = close_live_job_fence(job_id, message_id, exit_code=exit_code)
            finished = True
            body = closed.body if closed is not None else before
            _flush_fence_to_chat(
                thread_id=thread_id,
                message_id=message_id,
                job_id=job_id,
                command=command,
                body=body,
                closed=True,
                exit_code=exit_code,
            )
            with _lock:
                record = _jobs.get(job_id)
                if record is not None:
                    record["status"] = "completed" if exit_code == 0 else "failed"
                    record["exit_code"] = exit_code
                    record["finished_at"] = _utc_now()
            unsub = _tee_unsubscribers.pop(job_id, None)
            if unsub is not None:
                unsub()
            from app.chat.chat_stream_defer import release_deferred_chat_stream_if_idle

            release_deferred_chat_stream_if_idle(message_id)

    def on_closed() -> None:
        nonlocal buffer, finished
        with state_lock:
            if finished:
                return
            if buffer:
                append_live_job_fence_body(job_id, message_id, buffer)
                buffer = ""
            closed = close_live_job_fence(job_id, message_id, exit_code=None)
            finished = True
            body = closed.body if closed is not None else ""
            _flush_fence_to_chat(
                thread_id=thread_id,
                message_id=message_id,
                job_id=job_id,
                command=command,
                body=body,
                closed=True,
                exit_code=None,
            )
            with _lock:
                record = _jobs.get(job_id)
                if record is not None and record.get("status") == "running":
                    record["status"] = "completed"
                    record["finished_at"] = _utc_now()
        unsub = _tee_unsubscribers.pop(job_id, None)
        if unsub is not None:
            unsub()
        from app.chat.chat_stream_defer import release_deferred_chat_stream_if_idle

        release_deferred_chat_stream_if_idle(message_id)

    unsub = runtime.pty.subscribe(on_output, on_closed)
    with _lock:
        _tee_unsubscribers[job_id] = unsub
    # Silence unused workspace_id for API symmetry / future scoping.
    _ = workspace_id


def enqueue_agent_terminal_job(
    *,
    workspace_id: str,
    command: str,
    run_id: str | None = None,
    stream_to_chat: bool | None = None,
    thread_id: str | None = None,
    message_id: str | None = None,
    source_workspace_id: str | None = None,
) -> dict[str, Any]:
    """Ensure agent PTY runtime, write the command, return a chat-friendly receipt."""
    clean_workspace = str(workspace_id or "").strip()
    if not clean_workspace:
        raise ValueError("workspace_id is required")

    payload = _agent_command_bytes(command)
    if payload is None:
        raise ValueError("command is required")

    command_text = payload.decode("utf-8", errors="replace").rstrip("\n")
    assert_ship_command_allowed(
        workspace_id=clean_workspace,
        command=command_text,
        source_workspace_id=source_workspace_id,
    )
    should_stream = (
        bool(stream_to_chat)
        if stream_to_chat is not None
        else is_long_running_ship_shell(command_text)
    )

    clean_run = str(run_id or "").strip() or f"job-{uuid4().hex[:12]}"
    try:
        workspace_root = resolve_workspace_root(clean_workspace)
    except WorkspaceRootError as exc:
        raise ValueError(str(exc)) from exc

    session = ensure_agent_session(workspace_id=clean_workspace, run_id=clean_run)
    runtime = ensure_runtime(
        workspace_id=clean_workspace,
        workspace_root=str(workspace_root),
        session=session,
    )

    job_id = f"agent-job-{uuid4().hex[:12]}"
    created_at = _utc_now()
    stream_target = (
        _resolve_stream_target(
            workspace_id=clean_workspace,
            thread_id=thread_id,
            message_id=message_id,
        )
        if should_stream
        else None
    )

    write_command = command_text
    if stream_target is not None:
        write_command = _wrap_with_exit_sentinel(command_text)
        _start_chat_tee(
            job_id=job_id,
            workspace_id=clean_workspace,
            command=command_text,
            thread_id=stream_target[0],
            message_id=stream_target[1],
            runtime=runtime,
        )

    runtime.pty.write(f"{write_command}\n".encode("utf-8"))

    receipt = (
        f"Running in Axon terminal (`{session.session_id}`): `{command_text}`.\n"
        "Open the vaxon tab for live logs — this is Axon-owned, not Cursor shell detach."
    )
    if stream_target is not None:
        receipt += " Live output is also streaming into the active chat `:::terminal` card."

    record: dict[str, Any] = {
        "job_id": job_id,
        "workspace_id": clean_workspace,
        "session_id": session.session_id,
        "run_id": session.run_id,
        "command": command_text,
        "status": "running",
        "created_at": created_at,
        "stream_to_chat": stream_target is not None,
        "thread_id": stream_target[0] if stream_target else None,
        "message_id": stream_target[1] if stream_target else None,
        "receipt": receipt,
        "agent_terminal_session": serialize_session(session),
    }
    with _lock:
        _jobs[job_id] = deepcopy(record)
    return deepcopy(record)


def get_agent_terminal_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        record = _jobs.get(str(job_id or "").strip())
        return deepcopy(record) if record is not None else None


def list_agent_terminal_jobs(workspace_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    clean = str(workspace_id or "").strip()
    with _lock:
        items = [
            deepcopy(record)
            for record in _jobs.values()
            if str(record.get("workspace_id") or "") == clean
        ]
    items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return items[: max(1, min(int(limit), 100))]


def reset_agent_terminal_jobs() -> None:
    with _lock:
        unsubs = list(_tee_unsubscribers.values())
        _tee_unsubscribers.clear()
        _jobs.clear()
    for unsub in unsubs:
        try:
            unsub()
        except Exception:  # noqa: BLE001
            pass
    reset_live_job_fences()


__all__ = [
    "enqueue_agent_terminal_job",
    "get_agent_terminal_job",
    "list_agent_terminal_jobs",
    "reset_agent_terminal_jobs",
]
