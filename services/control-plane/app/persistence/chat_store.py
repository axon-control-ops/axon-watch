"""Persisted SQLite chat storage for the control-plane composer slice."""

from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
import os
from typing import Any
from uuid import uuid4

from app.persistence import run_store_sqlite

_MESSAGE_COLUMNS = (
    "message_id",
    "thread_id",
    "workspace_id",
    "run_id",
    "role",
    "content",
    "created_at",
)

_THREAD_COLUMNS = (
    "thread_id",
    "workspace_id",
    "run_id",
    "thread_kind",
    "created_at",
    "updated_at",
)


class ChatThreadNotFoundError(LookupError):
    pass


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


def reset_store() -> None:
    """Test-only wipe. Refuses to clear the live operator DB without an explicit allow flag."""
    db_path = run_store_sqlite.resolve_db_path(_configured_db_path())
    allow = os.environ.get("AXON_WATCH_ALLOW_STORE_RESET", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    path_text = str(db_path).replace("\\", "/")
    if path_text.endswith("/.local/state/control-plane.sqlite3") and not allow:
        raise RuntimeError(
            "refusing to wipe live chat store at "
            f"{db_path}; set AXON_WATCH_ALLOW_STORE_RESET=1 only for intentional recovery/tests"
        )
    with _managed_connection() as connection:
        connection.execute("DELETE FROM chat_messages")
        connection.execute("DELETE FROM chat_threads")
        connection.commit()


def _message_row_to_record(row: Any) -> dict[str, Any]:
    return {
        "message_id": row["message_id"],
        "thread_id": row["thread_id"],
        "workspace_id": row["workspace_id"],
        "run_id": row["run_id"],
        "role": row["role"],
        "content": row["content"],
        "created_at": row["created_at"],
    }


def _thread_row_to_record(row: Any) -> dict[str, Any]:
    return {
        "thread_id": row["thread_id"],
        "workspace_id": row["workspace_id"],
        "run_id": row["run_id"],
        "thread_kind": str(row["thread_kind"] if "thread_kind" in row.keys() else "operator"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_thread(
    *,
    workspace_id: str,
    run_id: str | None,
    created_at: str,
    thread_kind: str = "operator",
) -> dict[str, Any]:
    thread_id = f"thread_{uuid4().hex}"
    kind = str(thread_kind or "operator").strip().lower() or "operator"
    if kind not in {"operator", "ide"}:
        kind = "operator"
    record = {
        "thread_id": thread_id,
        "workspace_id": workspace_id,
        "run_id": run_id,
        "thread_kind": kind,
        "created_at": created_at,
        "updated_at": created_at,
    }
    with _managed_connection() as connection:
        connection.execute(
            f"""
            INSERT INTO chat_threads ({", ".join(_THREAD_COLUMNS)})
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record["thread_id"],
                record["workspace_id"],
                record["run_id"],
                record["thread_kind"],
                record["created_at"],
                record["updated_at"],
            ),
        )
        connection.commit()
    return deepcopy(record)


def get_thread(thread_id: str) -> dict[str, Any] | None:
    with _managed_connection() as connection:
        row = connection.execute(
            "SELECT * FROM chat_threads WHERE thread_id = ?",
            (thread_id,),
        ).fetchone()
    return _thread_row_to_record(row) if row is not None else None


def list_threads_for_workspace(
    workspace_id: str,
    *,
    thread_kind: str = "operator",
    limit: int = 25,
) -> list[dict[str, Any]]:
    kind = str(thread_kind or "operator").strip().lower() or "operator"
    max_limit = max(1, min(50, int(limit or 25)))
    with _managed_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM chat_threads
            WHERE workspace_id = ? AND thread_kind = ?
            ORDER BY updated_at DESC, created_at DESC, rowid DESC
            LIMIT ?
            """,
            (workspace_id, kind, max_limit),
        ).fetchall()
    return [_thread_row_to_record(row) for row in rows]


def first_operator_message_preview(thread_id: str, *, max_chars: int = 72) -> str:
    with _managed_connection() as connection:
        row = connection.execute(
            """
            SELECT content
            FROM chat_messages
            WHERE thread_id = ? AND role = 'operator'
            ORDER BY rowid ASC
            LIMIT 1
            """,
            (thread_id,),
        ).fetchone()
    if row is None:
        return "New chat"
    preview = str(row["content"] or "").strip().replace("\n", " ")
    if not preview:
        return "New chat"
    if len(preview) <= max_chars:
        return preview
    return f"{preview[: max_chars - 1].rstrip()}…"


def get_latest_thread_for_workspace(
    workspace_id: str,
    *,
    thread_kind: str = "operator",
) -> dict[str, Any] | None:
    kind = str(thread_kind or "operator").strip().lower() or "operator"
    with _managed_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM chat_threads
            WHERE workspace_id = ? AND thread_kind = ?
            ORDER BY updated_at DESC, created_at DESC, rowid DESC
            LIMIT 1
            """,
            (workspace_id, kind),
        ).fetchone()
    return _thread_row_to_record(row) if row is not None else None


def save_message(record: dict[str, Any]) -> dict[str, Any]:
    stored = deepcopy(record)
    with _managed_connection() as connection:
        connection.execute(
            f"""
            INSERT INTO chat_messages ({", ".join(_MESSAGE_COLUMNS)})
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stored["message_id"],
                stored["thread_id"],
                stored["workspace_id"],
                stored["run_id"],
                stored["role"],
                stored["content"],
                stored["created_at"],
            ),
        )
        connection.execute(
            """
            UPDATE chat_threads
            SET updated_at = ?, run_id = COALESCE(?, run_id)
            WHERE thread_id = ?
            """,
            (stored["created_at"], stored["run_id"], stored["thread_id"]),
        )
        connection.commit()
    return deepcopy(stored)


def update_message_content(*, message_id: str, content: str, updated_at: str) -> dict[str, Any] | None:
    clean_message_id = str(message_id or "").strip()
    if not clean_message_id:
        return None
    with _managed_connection() as connection:
        row = connection.execute(
            "SELECT * FROM chat_messages WHERE message_id = ?",
            (clean_message_id,),
        ).fetchone()
        if row is None:
            return None
        connection.execute(
            """
            UPDATE chat_messages
            SET content = ?
            WHERE message_id = ?
            """,
            (content, clean_message_id),
        )
        connection.execute(
            """
            UPDATE chat_threads
            SET updated_at = ?
            WHERE thread_id = ?
            """,
            (updated_at, row["thread_id"]),
        )
        connection.commit()
        updated = connection.execute(
            "SELECT * FROM chat_messages WHERE message_id = ?",
            (clean_message_id,),
        ).fetchone()
    return _message_row_to_record(updated) if updated is not None else None


def list_thread_messages(thread_id: str) -> list[dict[str, Any]]:
    with _managed_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM chat_messages
            WHERE thread_id = ?
            ORDER BY rowid ASC
            """,
            (thread_id,),
        ).fetchall()
    return [_message_row_to_record(row) for row in rows]


def list_threads(*, limit: int = 50) -> list[dict[str, Any]]:
    max_limit = max(1, min(100, int(limit or 50)))
    with _managed_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM chat_threads
            ORDER BY updated_at DESC, created_at DESC, rowid DESC
            LIMIT ?
            """,
            (max_limit,),
        ).fetchall()
    return [_thread_row_to_record(row) for row in rows]


def count_threads() -> int:
    with _managed_connection() as connection:
        row = connection.execute("SELECT COUNT(*) FROM chat_threads").fetchone()
    return int(row[0]) if row is not None else 0


def list_recent_messages(*, limit: int = 50) -> list[dict[str, Any]]:
    max_limit = max(1, min(100, int(limit or 50)))
    with _managed_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM chat_messages
            ORDER BY rowid DESC
            LIMIT ?
            """,
            (max_limit,),
        ).fetchall()
    return [_message_row_to_record(row) for row in rows]


def count_messages() -> int:
    with _managed_connection() as connection:
        row = connection.execute("SELECT COUNT(*) FROM chat_messages").fetchone()
    return int(row[0]) if row is not None else 0
