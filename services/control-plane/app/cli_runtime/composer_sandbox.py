"""Real per-workspace disposable isolation for the Agent Dock composer's Sandbox toggle.

The toggle previously only flipped a global boolean gating an unrelated
feature (the safe-improvement proposal pipeline) — it never changed where
composer messages actually dispatched, so "edits stay in a disposable copy"
was false. This reuses the same git-worktree isolation primitive continuous
workers already use (`app/safe_improvement/isolated_executor.py`) so the
claim is true.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.safe_improvement.isolated_executor import (
    IsolationError,
    agent_workspace_for_isolation,
    cleanup_isolation_root,
    create_isolation_root,
)
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root

_LOCK = threading.Lock()
_SESSIONS: dict[str, Path] = {}


def _status(workspace_id: str, *, enabled: bool) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "session_enabled": enabled,
        "env_forced": False,
        "source": "session" if enabled else "off",
    }


def sandbox_status(workspace_id: str) -> dict[str, Any]:
    cleaned = str(workspace_id or "").strip()
    with _LOCK:
        enabled = cleaned in _SESSIONS
    return _status(cleaned, enabled=enabled)


def enable_sandbox(workspace_id: str) -> dict[str, Any]:
    cleaned = str(workspace_id or "").strip()
    if not cleaned:
        raise ValueError("workspace_id is required")
    with _LOCK:
        if cleaned in _SESSIONS:
            return _status(cleaned, enabled=True)
    bound = resolve_workspace_root(cleaned)
    root = create_isolation_root(
        proposal_id=f"composer-{cleaned}-{uuid4().hex[:8]}",
        bound_project_root=bound,
    )
    with _LOCK:
        # Another request may have won the race while we were creating ours.
        if cleaned in _SESSIONS:
            cleanup_isolation_root(root)
            return _status(cleaned, enabled=True)
        _SESSIONS[cleaned] = root
    return _status(cleaned, enabled=True)


def disable_sandbox(workspace_id: str) -> dict[str, Any]:
    cleaned = str(workspace_id or "").strip()
    with _LOCK:
        root = _SESSIONS.pop(cleaned, None)
    if root is not None:
        cleanup_isolation_root(root)
    return _status(cleaned, enabled=False)


def resolve_sandbox_workspace_root(workspace_id: str) -> Path | None:
    """The isolated checkout to dispatch into, or None if sandbox isn't enabled."""
    cleaned = str(workspace_id or "").strip()
    with _LOCK:
        root = _SESSIONS.get(cleaned)
    if root is None:
        return None
    try:
        return agent_workspace_for_isolation(root)
    except IsolationError:
        return None


__all__ = [
    "IsolationError",
    "WorkspaceRootError",
    "disable_sandbox",
    "enable_sandbox",
    "resolve_sandbox_workspace_root",
    "sandbox_status",
]
