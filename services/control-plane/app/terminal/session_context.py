"""Per-session working-directory context for terminal tabs.

A terminal tab that says ``development`` while the agent is actually editing an
isolated worktree is actively misleading: the operator reads the bound branch
and assumes that is where the work landed. Sessions therefore report the cwd
and branch they are really rooted at, so the UI can label the isolated lane.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from app.terminal.session_registry import SANDBOX_SESSION_ID
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root


def _branch_name(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (result.stdout or "").strip() if result.returncode == 0 else ""


def session_root_context(workspace_id: str, session_id: str) -> dict[str, Any]:
    """Resolve where a session's PTY is actually rooted, and on which branch.

    Never raises: a tab label must not be able to break the session list.
    """
    clean_workspace = str(workspace_id or "").strip()
    clean_session = str(session_id or "").strip()
    isolated = clean_session == SANDBOX_SESSION_ID

    root: Path | None = None
    try:
        if isolated:
            from app.cli_runtime.composer_sandbox import resolve_sandbox_workspace_root

            root = resolve_sandbox_workspace_root(clean_workspace)
        else:
            root = resolve_workspace_root(clean_workspace)
    except (WorkspaceRootError, OSError, ValueError):
        root = None

    if root is None or not root.is_dir():
        return {"cwd": "", "branch": "", "isolated": isolated}
    return {"cwd": str(root), "branch": _branch_name(root), "isolated": isolated}


__all__ = ["session_root_context"]
