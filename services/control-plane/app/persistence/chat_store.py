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
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_thread(*, workspace_id: str, run_id: str | None, created_at: str) -> dict[str, Any]:
    thread_id = f"thread_{uuid4().hex}"
    record = {
        "thread_id": thread_id,
        "workspace_id": workspace_id,
        "run_id": run_id,
        "created_at": created_at,
        "updated_at": created_at,
    }
    with _managed_connection() as connection:
        connection.execute(
            f"""
            INSERT INTO chat_threads ({", ".join(_THREAD_COLUMNS)})
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record["thread_id"],
                record["workspace_id"],
                record["run_id"],
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


def get_latest_thread_for_workspace(workspace_id: str) -> dict[str, Any] | None:
    with _managed_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM chat_threads
            WHERE workspace_id = ?
            ORDER BY updated_at DESC, created_at DESC, rowid DESC
            LIMIT 1
            """,
            (workspace_id,),
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


def list_thread_messages(thread_id: str) -> list[dict[str, Any]]:
    with _managed_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM chat_messages
            WHERE thread_id = ?
            ORDER BY created_at ASC, message_id ASC
            """,
            (thread_id,),
        ).fetchall()
    return [_message_row_to_record(row) for row in rows]
