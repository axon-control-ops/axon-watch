"""Axon-owned agent-terminal jobs (not Cursor shellToolCall detach).

Enqueue a command into the persistent agent PTY so the operator can watch live
logs in the vaxon tab. Optional ``stream_to_chat`` tees PTY output into an open
``:::terminal`` fence on the active assistant message.

Job state lives in ``agent_job_registry``; ``agent_job_watcher`` drives every
job to a terminal state and enforces its deadline.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.cli_runtime.long_running_shell import is_long_running_ship_shell
from app.terminal.active_chat_stream import get_active_chat_stream
from app.terminal.agent_job_access import assert_agent_terminal_job_allowed
from app.terminal.agent_job_registry import (
    TERMINAL_STATUSES,
    get_agent_terminal_job,
    job_interrupt,
    list_agent_terminal_jobs,
    mark_job_finished,
    register_job,
    reset_agent_terminal_jobs,
    set_job_receipt,
    utc_now,
)
from app.terminal.agent_job_watcher import (
    resolve_timeout_seconds,
    start_job_watcher,
    wrap_with_exit_sentinel,
)
from app.terminal.session_registry import (
    ensure_agent_session,
    ensure_sandbox_session,
    serialize_session,
)
from app.terminal.session_runtime import ensure_runtime
from app.terminal.ship_command_guards import assert_ship_command_allowed
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root

_MAX_COMMAND_CHARS = 32_768

TARGET_WORKSPACE = "workspace"
TARGET_SANDBOX = "sandbox"
_TARGETS = frozenset({TARGET_WORKSPACE, TARGET_SANDBOX})


def _resolve_job_root(workspace_id: str, target: str) -> Path:
    """Resolve the cwd for a job. Sandbox targets never fall back to the root.

    A silent fallback would run a preview against the bound project root while
    the operator believes they are looking at sandbox-only changes, which is
    exactly the confusion this target is meant to remove.
    """
    if target == TARGET_SANDBOX:
        from app.cli_runtime.composer_sandbox import resolve_sandbox_workspace_root

        root = resolve_sandbox_workspace_root(workspace_id)
        if root is None:
            raise ValueError(
                "sandbox target requires an enabled, materialized sandbox for this workspace"
            )
        return root
    try:
        return resolve_workspace_root(workspace_id)
    except WorkspaceRootError as exc:
        raise ValueError(str(exc)) from exc


def _agent_command_bytes(value: object) -> bytes | None:
    if not isinstance(value, str):
        return None
    command = value.strip()
    if not command or len(command) > _MAX_COMMAND_CHARS or "\x00" in command:
        return None
    return f"{command}\n".encode("utf-8")


def _resolve_stream_target(
    *,
    workspace_id: str,
    thread_id: str | None,
    message_id: str | None,
) -> tuple[str, str] | None:
    from app.persistence import chat_store

    clean_thread = str(thread_id or "").strip()
    clean_message = str(message_id or "").strip()
    if clean_thread and clean_message:
        thread = chat_store.get_thread(clean_thread)
        message = chat_store.get_message(clean_message)
        if (
            thread is not None
            and message is not None
            and str(thread.get("workspace_id") or "") == str(workspace_id or "").strip()
            and str(message.get("thread_id") or "") == clean_thread
        ):
            return clean_thread, clean_message
        return None
    active = get_active_chat_stream(workspace_id)
    if active is None:
        return None
    thread = chat_store.get_thread(active.thread_id)
    message = chat_store.get_message(active.message_id)
    if (
        thread is None
        or message is None
        or str(thread.get("workspace_id") or "") != str(workspace_id or "").strip()
        or str(message.get("thread_id") or "") != active.thread_id
    ):
        return None
    return active.thread_id, active.message_id


def enqueue_agent_terminal_job(
    *,
    workspace_id: str,
    command: str,
    run_id: str | None = None,
    stream_to_chat: bool | None = None,
    thread_id: str | None = None,
    message_id: str | None = None,
    source_workspace_id: str | None = None,
    timeout_seconds: float | int | None = None,
    target: str = TARGET_WORKSPACE,
    service: bool = False,
) -> dict[str, Any]:
    """Ensure agent PTY runtime, write the command, return a chat-friendly receipt."""
    clean_workspace = str(workspace_id or "").strip()
    if not clean_workspace:
        raise ValueError("workspace_id is required")

    clean_target = str(target or TARGET_WORKSPACE).strip().lower() or TARGET_WORKSPACE
    if clean_target not in _TARGETS:
        raise ValueError(f"unsupported job target: {target!r}")

    payload = _agent_command_bytes(command)
    if payload is None:
        raise ValueError("command is required")

    command_text = payload.decode("utf-8", errors="replace").rstrip("\n")
    assert_ship_command_allowed(
        workspace_id=clean_workspace,
        command=command_text,
        source_workspace_id=source_workspace_id,
    )
    assert_agent_terminal_job_allowed(
        workspace_id=clean_workspace,
        source_workspace_id=source_workspace_id,
        run_id=run_id,
        command=command_text,
    )
    should_stream = (
        bool(stream_to_chat)
        if stream_to_chat is not None
        else is_long_running_ship_shell(command_text)
    )

    clean_run = str(run_id or "").strip() or f"job-{uuid4().hex[:12]}"
    workspace_root = _resolve_job_root(clean_workspace, clean_target)

    session = (
        ensure_sandbox_session(workspace_id=clean_workspace, run_id=clean_run)
        if clean_target == TARGET_SANDBOX
        else ensure_agent_session(workspace_id=clean_workspace, run_id=clean_run)
    )
    runtime = ensure_runtime(
        workspace_id=clean_workspace,
        workspace_root=str(workspace_root),
        session=session,
    )

    job_id = f"agent-job-{uuid4().hex[:12]}"
    stream_target = (
        _resolve_stream_target(
            workspace_id=clean_workspace,
            thread_id=thread_id,
            message_id=message_id,
        )
        if should_stream
        else None
    )

    deadline_seconds = resolve_timeout_seconds(
        timeout_seconds, command=command_text, service=service
    )
    record: dict[str, Any] = {
        "job_id": job_id,
        "workspace_id": clean_workspace,
        "session_id": session.session_id,
        "run_id": clean_run,
        "command": command_text,
        "target": clean_target,
        "cwd": str(workspace_root),
        "status": "running",
        "created_at": utc_now(),
        "timeout_seconds": int(deadline_seconds),
        "stream_to_chat": stream_target is not None,
        "thread_id": stream_target[0] if stream_target else None,
        "message_id": stream_target[1] if stream_target else None,
        "output_tail": "",
        "agent_terminal_session": serialize_session(session),
    }
    register_job(record)

    def _dispatch_to_session() -> None:
        start_job_watcher(
            job_id=job_id,
            command=command_text,
            runtime=runtime,
            chat_target=stream_target,
            timeout_seconds=deadline_seconds,
        )
        runtime.pty.write(f"{wrap_with_exit_sentinel(command_text, job_id)}\n".encode("utf-8"))

    from app.terminal.agent_job_session_queue import enqueue_session_job

    enqueue_session_job(
        workspace_id=clean_workspace,
        session_id=session.session_id,
        dispatch=_dispatch_to_session,
    )

    receipt = (
        f"Running in Axon terminal (`{session.session_id}`): `{command_text}`.\n"
        f"Working directory: `{workspace_root}`.\n"
        "Open the vaxon tab for live logs — this is Axon-owned, not Cursor shell detach."
    )
    if clean_target == TARGET_SANDBOX:
        receipt += " This job runs against the Sandbox checkout, not the bound project root."
    if stream_target is not None:
        receipt += " Live output is also streaming into the active chat `:::terminal` card."

    # Read back through the registry: the watcher may already have advanced
    # status/output while the command was being written.
    live = set_job_receipt(job_id, receipt)
    if live is not None:
        return live
    record["receipt"] = receipt
    return deepcopy(record)


def cancel_agent_terminal_job(job_id: str) -> dict[str, Any] | None:
    """Interrupt a running job and close it out as cancelled.

    Without this an operator (or a recovering agent) had no way to stop a hung
    command short of tearing down the whole PTY session.
    """
    clean = str(job_id or "").strip()
    if not clean:
        return None
    record = get_agent_terminal_job(clean)
    if record is None:
        return None
    if str(record.get("status") or "") in TERMINAL_STATUSES:
        return record

    interrupt = job_interrupt(clean)
    if interrupt is None:
        # No live watcher (e.g. after a restart): close the record out anyway.
        mark_job_finished(
            clean,
            status="cancelled",
            exit_code=None,
            note="cancelled by operator",
        )
        return get_agent_terminal_job(clean)
    interrupt(status="cancelled", note="cancelled by operator; sent SIGINT")
    return get_agent_terminal_job(clean)


__all__ = [
    "TARGET_SANDBOX",
    "TARGET_WORKSPACE",
    "cancel_agent_terminal_job",
    "enqueue_agent_terminal_job",
    "get_agent_terminal_job",
    "list_agent_terminal_jobs",
    "reset_agent_terminal_jobs",
]
