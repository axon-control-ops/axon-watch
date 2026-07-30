"""Persisted workspace handoff records for cross-workspace orchestration."""

from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
import os
import uuid
from typing import Any

from app.persistence import run_store_sqlite

_HANDOFF_COLUMNS = (
    "handoff_id",
    "source_workspace_id",
    "target_workspace_id",
    "task",
    "reason",
    "status",
    "target_task_id",
    "routed_role",
    "routed_employee_id",
    "communication_thread_id",
    "source_communication_thread_id",
    "created_at",
    "updated_at",
)

_OPTIONAL_COLUMNS: tuple[tuple[str, str], ...] = (
    ("target_task_id", "TEXT"),
    ("routed_role", "TEXT NOT NULL DEFAULT ''"),
    ("routed_employee_id", "TEXT NOT NULL DEFAULT ''"),
    ("communication_thread_id", "TEXT"),
    ("source_communication_thread_id", "TEXT"),
)


def _configured_db_path() -> str | None:
    return os.environ.get("AXON_WATCH_CONTROL_PLANE_DB")


def _connection():
    return run_store_sqlite.connect(_configured_db_path())


@contextmanager
def _managed_connection():
    connection = _connection()
    try:
        yield connection
    finally:
        connection.close()


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def ensure_handoff_schema(connection: Any) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_handoffs (
            handoff_id TEXT PRIMARY KEY,
            source_workspace_id TEXT NOT NULL,
            target_workspace_id TEXT NOT NULL,
            task TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'recorded',
            target_task_id TEXT,
            routed_role TEXT NOT NULL DEFAULT '',
            routed_employee_id TEXT NOT NULL DEFAULT '',
            communication_thread_id TEXT,
            source_communication_thread_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    columns = {
        str(row["name"] if hasattr(row, "keys") else row[1])
        for row in connection.execute("PRAGMA table_info(workspace_handoffs)").fetchall()
    }
    for name, ddl in _OPTIONAL_COLUMNS:
        if name not in columns:
            connection.execute(f"ALTER TABLE workspace_handoffs ADD COLUMN {name} {ddl}")
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workspace_handoffs_source
            ON workspace_handoffs(source_workspace_id, created_at DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workspace_handoffs_target
            ON workspace_handoffs(target_workspace_id, created_at DESC)
        """
    )


def _row_to_record(row: Any) -> dict[str, Any]:
    keys = set(row.keys()) if hasattr(row, "keys") else set()

    def _get(name: str, default: Any = None) -> Any:
        if keys and name not in keys:
            return default
        try:
            value = row[name]
        except (KeyError, IndexError):
            return default
        return default if value is None and default is not None else value

    return {
        "handoff_id": row["handoff_id"],
        "source_workspace_id": row["source_workspace_id"],
        "target_workspace_id": row["target_workspace_id"],
        "task": row["task"],
        "reason": row["reason"] or "",
        "status": row["status"],
        "target_task_id": _get("target_task_id"),
        "routed_role": str(_get("routed_role", "") or ""),
        "routed_employee_id": str(_get("routed_employee_id", "") or ""),
        "communication_thread_id": _get("communication_thread_id"),
        "source_communication_thread_id": _get("source_communication_thread_id"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def reset_store() -> None:
    with _managed_connection() as connection:
        ensure_handoff_schema(connection)
        connection.execute("DELETE FROM workspace_handoffs")
        connection.commit()


def save_handoff(record: dict[str, Any]) -> dict[str, Any]:
    stored = {
        "handoff_id": str(record["handoff_id"]),
        "source_workspace_id": str(record["source_workspace_id"]),
        "target_workspace_id": str(record["target_workspace_id"]),
        "task": str(record["task"]),
        "reason": str(record.get("reason") or ""),
        "status": str(record.get("status") or "recorded"),
        "target_task_id": record.get("target_task_id"),
        "routed_role": str(record.get("routed_role") or ""),
        "routed_employee_id": str(record.get("routed_employee_id") or ""),
        "communication_thread_id": record.get("communication_thread_id"),
        "source_communication_thread_id": record.get("source_communication_thread_id"),
        "created_at": str(record["created_at"]),
        "updated_at": str(record["updated_at"]),
    }
    with _managed_connection() as connection:
        ensure_handoff_schema(connection)
        placeholders = ", ".join("?" for _ in _HANDOFF_COLUMNS)
        connection.execute(
            f"""
            INSERT INTO workspace_handoffs ({", ".join(_HANDOFF_COLUMNS)})
            VALUES ({placeholders})
            """,
            tuple(stored.get(column) for column in _HANDOFF_COLUMNS),
        )
        connection.commit()
    return deepcopy(stored)


def create_handoff_record(
    *,
    source_workspace_id: str,
    target_workspace_id: str,
    task: str,
    reason: str = "",
) -> dict[str, Any]:
    timestamp = _utc_now_iso()
    record = {
        "handoff_id": f"handoff-{uuid.uuid4().hex[:16]}",
        "source_workspace_id": source_workspace_id.strip(),
        "target_workspace_id": target_workspace_id.strip(),
        "task": task.strip(),
        "reason": reason.strip(),
        "status": "recorded",
        "target_task_id": None,
        "routed_role": "",
        "routed_employee_id": "",
        "communication_thread_id": None,
        "source_communication_thread_id": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    return save_handoff(record)


def update_handoff(handoff_id: str, **fields: Any) -> dict[str, Any] | None:
    cleaned_id = handoff_id.strip()
    if not cleaned_id:
        return None
    allowed = {
        "status",
        "target_task_id",
        "routed_role",
        "routed_employee_id",
        "communication_thread_id",
        "source_communication_thread_id",
        "task",
        "reason",
    }
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return get_handoff(cleaned_id)
    updates["updated_at"] = _utc_now_iso()
    assignments = ", ".join(f"{key} = ?" for key in updates)
    with _managed_connection() as connection:
        ensure_handoff_schema(connection)
        connection.execute(
            f"UPDATE workspace_handoffs SET {assignments} WHERE handoff_id = ?",
            (*updates.values(), cleaned_id),
        )
        connection.commit()
    return get_handoff(cleaned_id)


def get_handoff(handoff_id: str) -> dict[str, Any] | None:
    with _managed_connection() as connection:
        ensure_handoff_schema(connection)
        row = connection.execute(
            "SELECT * FROM workspace_handoffs WHERE handoff_id = ?",
            (handoff_id.strip(),),
        ).fetchone()
    return _row_to_record(row) if row is not None else None


def list_handoffs_for_workspace(workspace_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    normalized_id = workspace_id.strip()
    max_limit = max(1, min(100, int(limit or 20)))
    with _managed_connection() as connection:
        ensure_handoff_schema(connection)
        rows = connection.execute(
            """
            SELECT * FROM workspace_handoffs
            WHERE source_workspace_id = ? OR target_workspace_id = ?
            ORDER BY created_at DESC, handoff_id ASC
            LIMIT ?
            """,
            (normalized_id, normalized_id, max_limit),
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def list_recent_handoffs(*, limit: int = 50) -> list[dict[str, Any]]:
    max_limit = max(1, min(100, int(limit or 50)))
    with _managed_connection() as connection:
        ensure_handoff_schema(connection)
        rows = connection.execute(
            """
            SELECT * FROM workspace_handoffs
            ORDER BY created_at DESC, handoff_id ASC
            LIMIT ?
            """,
            (max_limit,),
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def list_open_follow_through_handoffs(*, limit: int = 50) -> list[dict[str, Any]]:
    """Handoffs whose target ticket is missing or still open/leased."""
    from app.persistence import task_store

    open_items: list[dict[str, Any]] = []
    for record in list_recent_handoffs(limit=max(1, min(100, int(limit or 50)))):
        status = str(record.get("status") or "").strip().lower()
        if status not in {"recorded", "routed"}:
            continue
        task_id = str(record.get("target_task_id") or "").strip()
        if not task_id:
            open_items.append(record)
            continue
        task = task_store.get_task(task_id)
        task_status = str((task or {}).get("status") or "").strip().lower()
        if task is None or task_status in {"open", "leased"}:
            open_items.append(record)
    return open_items


def count_handoffs() -> int:
    with _managed_connection() as connection:
        ensure_handoff_schema(connection)
        row = connection.execute("SELECT COUNT(*) FROM workspace_handoffs").fetchone()
    return int(row[0]) if row is not None else 0
