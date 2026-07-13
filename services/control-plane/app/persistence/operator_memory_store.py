"""Durable operator notes and research captures."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from typing import Any
from uuid import uuid4

from app.persistence import run_store_sqlite

_COLUMNS = (
    "memory_id",
    "workspace_id",
    "scope",
    "kind",
    "title",
    "content",
    "source_refs_json",
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


def _row_to_record(row: Any) -> dict[str, Any]:
    return {
        "memory_id": row["memory_id"],
        "workspace_id": row["workspace_id"],
        "scope": row["scope"],
        "kind": row["kind"],
        "title": row["title"],
        "content": row["content"],
        "source_refs": json.loads(row["source_refs_json"] or "[]"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_memory(
    *,
    workspace_id: str,
    scope: str,
    kind: str,
    title: str,
    content: str,
    source_refs: list[dict[str, Any]],
    created_at: str,
) -> dict[str, Any]:
    record = {
        "memory_id": f"memory_{uuid4().hex}",
        "workspace_id": workspace_id,
        "scope": scope,
        "kind": kind,
        "title": title,
        "content": content,
        "source_refs_json": json.dumps(source_refs, separators=(",", ":"), sort_keys=True),
        "created_at": created_at,
        "updated_at": created_at,
    }
    with _managed_connection() as connection:
        connection.execute(
            f"""
            INSERT INTO operator_memories ({", ".join(_COLUMNS)})
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(record[column] for column in _COLUMNS),
        )
        connection.commit()
    return _row_to_record(record)


def list_memories(
    *,
    workspace_id: str | None = None,
    kind: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    values: list[Any] = []
    if workspace_id:
        clauses.append("(workspace_id = ? OR workspace_id = '')")
        values.append(workspace_id)
    if kind:
        clauses.append("kind = ?")
        values.append(kind)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    max_limit = max(1, min(50, int(limit or 20)))
    with _managed_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM operator_memories
            {where}
            ORDER BY updated_at DESC, created_at DESC, rowid DESC
            LIMIT ?
            """,
            (*values, max_limit),
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def search_memories(
    query: str,
    *,
    workspace_id: str | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    trimmed = query.strip()
    if not trimmed:
        return []
    like = f"%{trimmed.lower()}%"
    values: list[Any] = [like, like]
    where = "(lower(title) LIKE ? OR lower(content) LIKE ?)"
    if workspace_id:
        where += " AND (workspace_id = ? OR workspace_id = '')"
        values.append(workspace_id)
    max_limit = max(1, min(20, int(limit or 8)))
    with _managed_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM operator_memories
            WHERE {where}
            ORDER BY updated_at DESC, created_at DESC, rowid DESC
            LIMIT ?
            """,
            (*values, max_limit),
        ).fetchall()
    return [_row_to_record(row) for row in rows]

