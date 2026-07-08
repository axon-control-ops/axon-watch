"""Persist recent VAXON voice turns for operator debugging."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.persistence import run_store_sqlite


def _configured_db_path() -> str | None:
    return os.environ.get("AXON_WATCH_CONTROL_PLANE_DB")


def _connect() -> sqlite3.Connection:
    return run_store_sqlite.connect(_configured_db_path())


def _ensure_voice_log_table(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS kairo_voice_log (
            entry_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            session_id TEXT NOT NULL,
            workspace_id TEXT,
            raw_content TEXT NOT NULL,
            normalized_content TEXT NOT NULL,
            reply TEXT NOT NULL,
            turn_kind TEXT NOT NULL,
            source TEXT NOT NULL,
            stt_note TEXT,
            duration_ms INTEGER,
            runtime_dispatched INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_kairo_voice_log_created
            ON kairo_voice_log(created_at DESC);
        """
    )
    columns = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info(kairo_voice_log)").fetchall()
    }
    if "duration_ms" not in columns:
        connection.execute("ALTER TABLE kairo_voice_log ADD COLUMN duration_ms INTEGER")
    if "runtime_dispatched" not in columns:
        connection.execute(
            "ALTER TABLE kairo_voice_log ADD COLUMN runtime_dispatched INTEGER NOT NULL DEFAULT 0"
        )


def append_voice_transcript(
    *,
    session_id: str,
    raw_content: str,
    normalized_content: str,
    reply: str,
    turn_kind: str,
    source: str,
    workspace_id: str | None = None,
    stt_note: str | None = None,
    duration_ms: int | None = None,
    runtime_dispatched: bool = False,
) -> dict[str, str]:
    entry_id = f"voice_{uuid4().hex[:12]}"
    created_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with _connect() as connection:
        _ensure_voice_log_table(connection)
        connection.execute(
            """
            INSERT INTO kairo_voice_log (
                entry_id, created_at, session_id, workspace_id,
                raw_content, normalized_content, reply, turn_kind, source, stt_note,
                duration_ms, runtime_dispatched
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_id,
                created_at,
                session_id.strip() or "default",
                workspace_id,
                raw_content,
                normalized_content,
                reply,
                turn_kind,
                source,
                stt_note,
                duration_ms,
                1 if runtime_dispatched else 0,
            ),
        )
        connection.commit()
    return {"entry_id": entry_id, "created_at": created_at}


def list_recent_voice_transcripts(*, limit: int = 20) -> list[dict[str, Any]]:
    capped = max(1, min(int(limit), 100))
    with _connect() as connection:
        _ensure_voice_log_table(connection)
        rows = connection.execute(
            """
            SELECT entry_id, created_at, session_id, workspace_id,
                   raw_content, normalized_content, reply, turn_kind, source, stt_note,
                   duration_ms, runtime_dispatched
            FROM kairo_voice_log
            ORDER BY created_at DESC, entry_id DESC
            LIMIT ?
            """,
            (capped,),
        ).fetchall()
    return [dict(row) for row in rows]
