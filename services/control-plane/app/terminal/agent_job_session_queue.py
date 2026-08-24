"""Serialize agent terminal writes per PTY session.

The workspace shares one ``terminal-agent`` PTY. Concurrent writes let a later
job inject into an interactive REPL or half-finished shell from an earlier job.
Jobs therefore queue their PTY dispatch until the session is idle.
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Callable

_lock = threading.Lock()
_active: dict[tuple[str, str], bool] = {}
_pending: dict[tuple[str, str], deque[Callable[[], None]]] = {}


def _session_key(workspace_id: str, session_id: str) -> tuple[str, str]:
    return (str(workspace_id or "").strip(), str(session_id or "").strip())


def enqueue_session_job(
    *,
    workspace_id: str,
    session_id: str,
    dispatch: Callable[[], None],
) -> None:
    """Run ``dispatch`` now when the session is idle, otherwise queue it."""
    key = _session_key(workspace_id, session_id)
    with _lock:
        if _active.get(key):
            _pending.setdefault(key, deque()).append(dispatch)
            return
        _active[key] = True

    try:
        dispatch()
    except Exception:
        notify_session_job_finished(workspace_id=workspace_id, session_id=session_id)
        raise


def notify_session_job_finished(*, workspace_id: str, session_id: str) -> None:
    """Release the session and dispatch the next queued job, if any."""
    key = _session_key(workspace_id, session_id)
    with _lock:
        queue = _pending.get(key)
        if queue and len(queue) > 0:
            next_dispatch = queue.popleft()
        else:
            _active[key] = False
            next_dispatch = None

    if next_dispatch is None:
        return

    try:
        next_dispatch()
    except Exception:
        notify_session_job_finished(workspace_id=workspace_id, session_id=session_id)
        raise


__all__ = ["enqueue_session_job", "notify_session_job_finished"]
