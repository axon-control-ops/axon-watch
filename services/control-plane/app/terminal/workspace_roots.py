"""Resolve workspace identifiers to on-disk roots for PTY attachment."""

from __future__ import annotations

import os
from pathlib import Path

from app.workspace_catalog import WorkspaceNotFoundError, get_workspace_record


class WorkspaceRootError(ValueError):
    pass


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def workspace_roots_base() -> Path:
    configured = os.environ.get("AXON_WATCH_WORKSPACE_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (_repo_root() / ".local" / "workspaces").resolve()


def resolve_workspace_root(workspace_id: str) -> Path:
    """Return the filesystem root for a known workspace identifier."""
    try:
        get_workspace_record(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise WorkspaceRootError(str(exc)) from exc

    workspace_id = workspace_id.strip()
    if not workspace_id:
        raise WorkspaceRootError("workspace_id is required")

    root = (workspace_roots_base() / workspace_id).resolve()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise WorkspaceRootError(f"unable to prepare workspace root: {root}") from exc

    if not root.is_dir():
        raise WorkspaceRootError(f"workspace root is not a directory: {root}")

    return root


def ensure_workspace_root(workspace_id: str) -> Path:
    """Alias used by tests and session bootstrap."""
    try:
        return resolve_workspace_root(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise WorkspaceRootError(str(exc)) from exc
