"""Persistent PTY runtimes keyed by workspace/session."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from app.terminal.pty_process import PtyProcess
from app.terminal.session_registry import TerminalSessionRecord


@dataclass
class TerminalSessionRuntime:
    workspace_id: str
    session_id: str
    role: str
    workspace_root: str
    pty: PtyProcess


_lock = Lock()
_runtimes: dict[tuple[str, str], TerminalSessionRuntime] = {}


def _runtime_key(workspace_id: str, session_id: str) -> tuple[str, str]:
    return (str(workspace_id or "").strip(), str(session_id or "").strip())


def ensure_runtime(
    *,
    workspace_id: str,
    workspace_root: str,
    session: TerminalSessionRecord,
) -> TerminalSessionRuntime:
    key = _runtime_key(workspace_id, session.session_id)
    with _lock:
        existing = _runtimes.get(key)
        if existing is not None and existing.pty.poll() is None:
            return existing

        if existing is not None:
            existing.pty.close()
            _runtimes.pop(key, None)

        runtime = TerminalSessionRuntime(
            workspace_id=str(workspace_id or "").strip(),
            session_id=session.session_id,
            role=session.role,
            workspace_root=str(workspace_root),
            pty=PtyProcess(str(workspace_root), session_id=session.session_id),
        )
        _runtimes[key] = runtime
        return runtime


def terminate_runtime(workspace_id: str, session_id: str) -> None:
    key = _runtime_key(workspace_id, session_id)
    with _lock:
        runtime = _runtimes.pop(key, None)
    if runtime is not None:
        runtime.pty.close()


def reset_runtimes() -> None:
    with _lock:
        runtimes = list(_runtimes.values())
        _runtimes.clear()
    for runtime in runtimes:
        runtime.pty.close()
