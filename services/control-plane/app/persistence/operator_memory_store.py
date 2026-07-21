"""Durable operator notes, research captures, and reminders."""

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
    "due_at",
    "snoozed_until",
    "trigger",
    "priority",
    "status",
    "last_presented_at",
    "dismiss_reason",
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
    keys = set(row.keys()) if hasattr(row, "keys") else set()
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
        "due_at": row["due_at"] if "due_at" in keys else "",
        "snoozed_until": row["snoozed_until"] if "snoozed_until" in keys else "",
        "trigger": row["trigger"] if "trigger" in keys else "",
        "priority": row["priority"] if "priority" in keys else "",
        "status": row["status"] if "status" in keys else "",
        "last_presented_at": row["last_presented_at"] if "last_presented_at" in keys else "",
        "dismiss_reason": row["dismiss_reason"] if "dismiss_reason" in keys else "",
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
    due_at: str = "",
    snoozed_until: str = "",
    trigger: str = "",
    priority: str = "",
    status: str = "",
    last_presented_at: str = "",
    dismiss_reason: str = "",
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
        "due_at": due_at or "",
        "snoozed_until": snoozed_until or "",
        "trigger": trigger or "",
        "priority": priority or ("normal" if kind in {"reminder", "open_loop"} else ""),
        "status": status or ("open" if kind in {"reminder", "open_loop"} else ""),
        "last_presented_at": last_presented_at or "",
        "dismiss_reason": dismiss_reason or "",
    }
    with _managed_connection() as connection:
        connection.execute(
            f"""
            INSERT INTO operator_memories ({", ".join(_COLUMNS)})
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(record[column] for column in _COLUMNS),
        )
        connection.commit()
    return _row_to_record(record)


def patch_memory(memory_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    trimmed_id = str(memory_id or "").strip()
    if not trimmed_id:
        return None
    with _managed_connection() as connection:
        row = connection.execute(
            "SELECT * FROM operator_memories WHERE memory_id = ?",
            (trimmed_id,),
        ).fetchone()
        if not row:
            return None
        current = _row_to_record(row)
        from app.host_context.models import utc_now_iso

        updated_at = utc_now_iso()
        next_record = {
            **current,
            **{key: value for key, value in patch.items() if value is not None},
            "updated_at": updated_at,
            "source_refs": current["source_refs"],
        }
        if "source_refs" in patch and isinstance(patch["source_refs"], list):
            next_record["source_refs"] = patch["source_refs"]
        connection.execute(
            """
            UPDATE operator_memories SET
                workspace_id = ?,
                scope = ?,
                kind = ?,
                title = ?,
                content = ?,
                source_refs_json = ?,
                updated_at = ?,
                due_at = ?,
                snoozed_until = ?,
                trigger = ?,
                priority = ?,
                status = ?,
                last_presented_at = ?,
                dismiss_reason = ?
            WHERE memory_id = ?
            """,
            (
                next_record["workspace_id"],
                next_record["scope"],
                next_record["kind"],
                next_record["title"],
                next_record["content"],
                json.dumps(next_record["source_refs"], separators=(",", ":"), sort_keys=True),
                next_record["updated_at"],
                next_record.get("due_at") or "",
                next_record.get("snoozed_until") or "",
                next_record.get("trigger") or "",
                next_record.get("priority") or "",
                next_record.get("status") or "",
                next_record.get("last_presented_at") or "",
                next_record.get("dismiss_reason") or "",
                trimmed_id,
            ),
        )
        connection.commit()
    return get_memory(trimmed_id)


def get_memory(memory_id: str) -> dict[str, Any] | None:
    with _managed_connection() as connection:
        row = connection.execute(
            "SELECT * FROM operator_memories WHERE memory_id = ?",
            (str(memory_id or "").strip(),),
        ).fetchone()
    return _row_to_record(row) if row else None


def list_memories(
    *,
    workspace_id: str | None = None,
    kind: str | None = None,
    limit: int = 20,
    include_reminders: bool = False,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    values: list[Any] = []
    if workspace_id:
        clauses.append("(workspace_id = ? OR workspace_id = '')")
        values.append(workspace_id)
    if kind:
        clauses.append("kind = ?")
        values.append(kind)
    elif not include_reminders:
        # Default list stays note-oriented unless caller opts into reminders.
        clauses.append("kind NOT IN ('reminder', 'open_loop')")
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
