"""Axon-owned agent-terminal jobs (not Cursor shellToolCall detach).

Enqueue a command into the persistent agent PTY so the operator can watch live
logs in the vaxon tab while chat keeps a short receipt. Cursor CLI still owns
its own shell tools; this path is for Axon-owned background work.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from app.terminal.session_registry import ensure_agent_session, serialize_session
from app.terminal.session_runtime import ensure_runtime
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root

_MAX_COMMAND_CHARS = 32_768
_lock = Lock()
_jobs: dict[str, dict[str, Any]] = {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _agent_command_bytes(value: object) -> bytes | None:
    if not isinstance(value, str):
        return None
    command = value.strip()
    if not command or len(command) > _MAX_COMMAND_CHARS or "\x00" in command:
        return None
    return f"{command}\n".encode("utf-8")


def enqueue_agent_terminal_job(
    *,
    workspace_id: str,
    command: str,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Ensure agent PTY runtime, write the command, return a chat-friendly receipt."""
    clean_workspace = str(workspace_id or "").strip()
    if not clean_workspace:
        raise ValueError("workspace_id is required")

    payload = _agent_command_bytes(command)
    if payload is None:
        raise ValueError("command is required")

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
    runtime.pty.write(payload)

    job_id = f"agent-job-{uuid4().hex[:12]}"
    command_text = payload.decode("utf-8", errors="replace").rstrip("\n")
    created_at = _utc_now()
    record: dict[str, Any] = {
        "job_id": job_id,
        "workspace_id": clean_workspace,
        "session_id": session.session_id,
        "run_id": session.run_id,
        "command": command_text,
        "status": "running",
        "created_at": created_at,
        "receipt": (
            f"Running in Axon terminal (`{session.session_id}`): `{command_text}`.\n"
            "Open the vaxon tab for live logs — this is Axon-owned, not Cursor shell detach."
        ),
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
        _jobs.clear()


__all__ = [
    "enqueue_agent_terminal_job",
    "get_agent_terminal_job",
    "list_agent_terminal_jobs",
    "reset_agent_terminal_jobs",
]
