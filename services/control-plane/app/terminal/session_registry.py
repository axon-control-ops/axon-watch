"""In-memory terminal session registry for workspace-scoped PTY lanes."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

_OPERATOR_SESSION_ID = "terminal-operator"


@dataclass(frozen=True)
class TerminalSessionRecord:
    session_id: str
    workspace_id: str
    role: str
    title: str
    run_id: str | None
    created_at: str


_lock = Lock()
_sessions: dict[tuple[str, str], TerminalSessionRecord] = {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _session_key(workspace_id: str, session_id: str) -> tuple[str, str]:
    return (str(workspace_id or "").strip(), str(session_id or "").strip())


def _normalize_role(role: str | None) -> str:
    clean = str(role or "operator").strip().lower() or "operator"
    return clean if clean in {"operator", "agent"} else "operator"


def ensure_operator_session(workspace_id: str) -> TerminalSessionRecord:
    clean_workspace_id = str(workspace_id or "").strip()
    if not clean_workspace_id:
        raise ValueError("workspace_id is required")

    key = _session_key(clean_workspace_id, _OPERATOR_SESSION_ID)
    with _lock:
        existing = _sessions.get(key)
        if existing is not None:
            return deepcopy(existing)

        record = TerminalSessionRecord(
            session_id=_OPERATOR_SESSION_ID,
            workspace_id=clean_workspace_id,
            role="operator",
            title="bash",
            run_id=None,
            created_at=_utc_now(),
        )
        _sessions[key] = record
        return deepcopy(record)


def create_session(
    *,
    workspace_id: str,
    role: str = "operator",
    title: str | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
) -> TerminalSessionRecord:
    clean_workspace_id = str(workspace_id or "").strip()
    if not clean_workspace_id:
        raise ValueError("workspace_id is required")

    normalized_role = _normalize_role(role)
    clean_run_id = str(run_id or "").strip() or None
    clean_session_id = str(session_id or "").strip()
    if not clean_session_id:
        clean_session_id = (
            f"terminal-agent-{clean_run_id[-8:]}"
            if normalized_role == "agent" and clean_run_id
            else f"terminal-{uuid4().hex[:10]}"
        )

    key = _session_key(clean_workspace_id, clean_session_id)
    with _lock:
        existing = _sessions.get(key)
        if existing is not None:
            return deepcopy(existing)

        resolved_title = str(title or "").strip()
        if not resolved_title:
            resolved_title = "vaxon" if normalized_role == "agent" else "bash"

        record = TerminalSessionRecord(
            session_id=clean_session_id,
            workspace_id=clean_workspace_id,
            role=normalized_role,
            title=resolved_title,
            run_id=clean_run_id,
            created_at=_utc_now(),
        )
        _sessions[key] = record
        return deepcopy(record)


def ensure_agent_session(*, workspace_id: str, run_id: str) -> TerminalSessionRecord:
    clean_run_id = str(run_id or "").strip()
    if not clean_run_id:
        raise ValueError("run_id is required for agent terminal sessions")
    return create_session(
        workspace_id=workspace_id,
        role="agent",
        title="vaxon",
        run_id=clean_run_id,
    )


def get_session(workspace_id: str, session_id: str) -> TerminalSessionRecord | None:
    key = _session_key(workspace_id, session_id)
    with _lock:
        record = _sessions.get(key)
        return deepcopy(record) if record is not None else None


def list_sessions(workspace_id: str) -> list[TerminalSessionRecord]:
    clean_workspace_id = str(workspace_id or "").strip()
    with _lock:
        records = [
            deepcopy(record)
            for (ws_id, _), record in _sessions.items()
            if ws_id == clean_workspace_id
        ]
    records.sort(key=lambda item: item.created_at)
    if not any(item.session_id == _OPERATOR_SESSION_ID for item in records):
        records.insert(0, ensure_operator_session(clean_workspace_id))
    return records


def rename_session(workspace_id: str, session_id: str, title: str) -> TerminalSessionRecord | None:
    clean_title = str(title or "").strip()
    if not clean_title:
        return None
    key = _session_key(workspace_id, session_id)
    with _lock:
        record = _sessions.get(key)
        if record is None:
            return None
        updated = TerminalSessionRecord(
            session_id=record.session_id,
            workspace_id=record.workspace_id,
            role=record.role,
            title=clean_title,
            run_id=record.run_id,
            created_at=record.created_at,
        )
        _sessions[key] = updated
        return deepcopy(updated)


def delete_session(workspace_id: str, session_id: str) -> bool:
    clean_session_id = str(session_id or "").strip()
    if clean_session_id == _OPERATOR_SESSION_ID:
        return False
    key = _session_key(workspace_id, clean_session_id)
    with _lock:
        removed = _sessions.pop(key, None)
    return removed is not None


def serialize_session(record: TerminalSessionRecord) -> dict[str, str | None]:
    return {
        "session_id": record.session_id,
        "workspace_id": record.workspace_id,
        "role": record.role,
        "title": record.title,
        "run_id": record.run_id,
        "created_at": record.created_at,
    }


def reset_registry() -> None:
    with _lock:
        _sessions.clear()
