"""Append and read NDJSON evidence lines for Debug-mode instrumentation."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def _candidate_roots() -> list[Path]:
    here = Path(__file__).resolve()
    # services/control-plane/app -> axon-watch repo root
    axon_watch_root = here.parents[3]
    roots = [axon_watch_root]
    # Sibling axon-local (Cursor project root for this debug session)
    sibling_local = axon_watch_root.parent / "axon-local"
    if sibling_local.is_dir():
        roots.append(sibling_local)
    return roots


def resolve_debug_session_log_path(workspace_id: str = "") -> Path:
    """Resolve `.axon/debug-session.ndjson` for a workspace (fallback: repo root)."""
    from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root

    workspace_root: Path | None = None
    cleaned = (workspace_id or "").strip() or "workspace_axon_watch"
    try:
        workspace_root = resolve_workspace_root(cleaned)
    except WorkspaceRootError:
        workspace_root = None
    if workspace_root is None:
        workspace_root = Path(__file__).resolve().parents[3]
    axon_dir = workspace_root / ".axon"
    axon_dir.mkdir(parents=True, exist_ok=True)
    return axon_dir / "debug-session.ndjson"


def read_debug_session_log_lines(
    *,
    workspace_id: str = "",
    limit: int = 80,
) -> list[dict[str, Any]]:
    """Return the newest NDJSON evidence lines for the Debug Mode thread panel."""
    path = resolve_debug_session_log_path(workspace_id)
    if not path.is_file():
        return []
    try:
        raw_lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    capped = max(1, min(int(limit or 80), 200))
    entries: list[dict[str, Any]] = []
    for line in raw_lines[-capped:]:
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def append_debug_session_log(
    *,
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict[str, Any] | None = None,
) -> None:
    if os.environ.get("AXON_DEBUG_SESSION_LOG") != "1":
        return

    payload = {
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    line = json.dumps(payload, ensure_ascii=True) + "\n"
    for root in _candidate_roots():
        axon_dir = root / ".axon"
        try:
            axon_dir.mkdir(parents=True, exist_ok=True)
            with (axon_dir / "debug-session.ndjson").open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError:
            continue
