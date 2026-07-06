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
    "created_at",
    "updated_at",
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


def _row_to_record(row: Any) -> dict[str, Any]:
    return {
        "handoff_id": row["handoff_id"],
        "source_workspace_id": row["source_workspace_id"],
        "target_workspace_id": row["target_workspace_id"],
        "task": row["task"],
        "reason": row["reason"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def reset_store() -> None:
    with _managed_connection() as connection:
        connection.execute("DELETE FROM workspace_handoffs")
        connection.commit()


def save_handoff(record: dict[str, Any]) -> dict[str, Any]:
    stored = deepcopy(record)
    with _managed_connection() as connection:
        placeholders = ", ".join("?" for _ in _HANDOFF_COLUMNS)
        connection.execute(
            f"""
            INSERT INTO workspace_handoffs ({", ".join(_HANDOFF_COLUMNS)})
            VALUES ({placeholders})
            """,
            tuple(stored[column] for column in _HANDOFF_COLUMNS),
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
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    return save_handoff(record)


def get_handoff(handoff_id: str) -> dict[str, Any] | None:
    with _managed_connection() as connection:
        row = connection.execute(
            "SELECT * FROM workspace_handoffs WHERE handoff_id = ?",
            (handoff_id.strip(),),
        ).fetchone()
    return _row_to_record(row) if row is not None else None


def list_handoffs_for_workspace(workspace_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    normalized_id = workspace_id.strip()
    max_limit = max(1, min(100, int(limit or 20)))
    with _managed_connection() as connection:
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
        rows = connection.execute(
            """
            SELECT * FROM workspace_handoffs
            ORDER BY created_at DESC, handoff_id ASC
            LIMIT ?
            """,
            (max_limit,),
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def count_handoffs() -> int:
    with _managed_connection() as connection:
        row = connection.execute("SELECT COUNT(*) FROM workspace_handoffs").fetchone()
    return int(row[0]) if row is not None else 0
