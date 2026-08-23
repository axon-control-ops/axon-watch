"""Durable operator intent and checkout metadata for composer sandboxes."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import os
from typing import Any
from uuid import uuid4

from app.persistence import run_store_sqlite
from app.persistence.schema_serialization import serialized_schema


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@contextmanager
def _connection():
    connection = run_store_sqlite.connect(os.environ.get("AXON_WATCH_CONTROL_PLANE_DB"))
    try:
        ensure_schema(connection)
        yield connection
    finally:
        connection.close()


@serialized_schema
def ensure_schema(connection: Any) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_composer_sandboxes (
            workspace_id TEXT PRIMARY KEY,
            manual_enabled INTEGER NOT NULL DEFAULT 0,
            checkout_id TEXT,
            checkout_root TEXT,
            retained_reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )


def get_state(workspace_id: str) -> dict[str, Any]:
    cleaned = str(workspace_id or "").strip()
    with _connection() as connection:
        row = connection.execute(
            "SELECT * FROM workspace_composer_sandboxes WHERE workspace_id = ?",
            (cleaned,),
        ).fetchone()
    if row is None:
        return {
            "workspace_id": cleaned,
            "manual_enabled": False,
            "checkout_id": None,
            "checkout_root": None,
            "retained_reason": "",
        }
    return {
        "workspace_id": cleaned,
        "manual_enabled": bool(row["manual_enabled"]),
        "checkout_id": row["checkout_id"],
        "checkout_root": row["checkout_root"],
        "retained_reason": str(row["retained_reason"] or ""),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def save_state(workspace_id: str, **fields: Any) -> dict[str, Any]:
    cleaned = str(workspace_id or "").strip()
    if not cleaned:
        raise ValueError("workspace_id is required")
    current = get_state(cleaned)
    timestamp = _now()
    record = {
        "workspace_id": cleaned,
        "manual_enabled": bool(fields.get("manual_enabled", current["manual_enabled"])),
        "checkout_id": fields.get("checkout_id", current.get("checkout_id")),
        "checkout_root": fields.get("checkout_root", current.get("checkout_root")),
        "retained_reason": str(fields.get("retained_reason", current.get("retained_reason") or "")),
        "created_at": str(current.get("created_at") or timestamp),
        "updated_at": timestamp,
    }
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO workspace_composer_sandboxes
                (workspace_id, manual_enabled, checkout_id, checkout_root,
                 retained_reason, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(workspace_id) DO UPDATE SET
                manual_enabled = excluded.manual_enabled,
                checkout_id = excluded.checkout_id,
                checkout_root = excluded.checkout_root,
                retained_reason = excluded.retained_reason,
                updated_at = excluded.updated_at
            """,
            (
                cleaned,
                int(record["manual_enabled"]),
                record["checkout_id"],
                record["checkout_root"],
                record["retained_reason"],
                record["created_at"],
                timestamp,
            ),
        )
        connection.commit()
    return get_state(cleaned)


def allocate_checkout_id(workspace_id: str) -> str:
    safe = "".join(ch if ch.isalnum() else "-" for ch in workspace_id).strip("-")[:40]
    return f"composer-{safe or 'workspace'}-{uuid4().hex[:8]}"


def list_states() -> list[dict[str, Any]]:
    with _connection() as connection:
        rows = connection.execute(
            "SELECT workspace_id FROM workspace_composer_sandboxes ORDER BY workspace_id"
        ).fetchall()
    return [get_state(str(row["workspace_id"])) for row in rows]


__all__ = ["allocate_checkout_id", "get_state", "list_states", "save_state"]
