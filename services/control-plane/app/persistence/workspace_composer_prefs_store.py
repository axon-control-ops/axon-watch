"""Per-workspace Agent Dock composer model prefs (server-side for workers)."""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from app.cli_runtime.model_policy import normalize_model_id
from app.persistence import run_store_sqlite


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
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def default_prefs() -> dict[str, Any]:
    return {
        "cursor_cli_model": "auto",
        "updated_at": None,
    }


def get_workspace_composer_prefs(workspace_id: str) -> dict[str, Any]:
    cleaned = str(workspace_id or "").strip()
    if not cleaned:
        return default_prefs()
    with _managed_connection() as connection:
        row = connection.execute(
            """
            SELECT cursor_cli_model, updated_at
            FROM workspace_composer_prefs
            WHERE workspace_id = ?
            """,
            (cleaned,),
        ).fetchone()
    if not row:
        return default_prefs()
    model = normalize_model_id(row["cursor_cli_model"]) or "auto"
    return {
        "cursor_cli_model": model if model else "auto",
        "updated_at": row["updated_at"],
    }


def set_workspace_composer_prefs(
    workspace_id: str,
    *,
    cursor_cli_model: str | None = None,
) -> dict[str, Any]:
    cleaned = str(workspace_id or "").strip()
    if not cleaned:
        raise ValueError("workspace_id is required")
    current = get_workspace_composer_prefs(cleaned)
    next_model = current["cursor_cli_model"]
    if cursor_cli_model is not None:
        next_model = normalize_model_id(cursor_cli_model) or "auto"
    updated_at = _utc_now_iso()
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO workspace_composer_prefs (workspace_id, cursor_cli_model, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(workspace_id) DO UPDATE SET
                cursor_cli_model = excluded.cursor_cli_model,
                updated_at = excluded.updated_at
            """,
            (cleaned, next_model, updated_at),
        )
        connection.commit()
    return {
        "cursor_cli_model": next_model,
        "updated_at": updated_at,
    }


def resolve_worker_runtime_model(workspace_id: str) -> str | None:
    """Model workers may pass into Lane B.

    Auto → None (omit --model). Composer or explicit API pin → that id.
    """
    prefs = get_workspace_composer_prefs(workspace_id)
    model = normalize_model_id(prefs.get("cursor_cli_model"))
    if not model or model.lower() == "auto":
        return None
    return model
