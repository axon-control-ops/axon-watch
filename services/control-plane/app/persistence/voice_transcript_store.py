"""Persist recent VAXON voice turns for operator debugging."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.persistence import run_store_sqlite


def _configured_db_path() -> str | None:
    return os.environ.get("AXON_WATCH_CONTROL_PLANE_DB")


def _connect() -> sqlite3.Connection:
    return run_store_sqlite.connect(_configured_db_path())


@contextmanager
def _managed_connection():
    connection = _connect()
    try:
        yield connection
    finally:
        connection.close()


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
    migrations = {
        "duration_ms": "ALTER TABLE kairo_voice_log ADD COLUMN duration_ms INTEGER",
        "runtime_dispatched": (
            "ALTER TABLE kairo_voice_log ADD COLUMN runtime_dispatched INTEGER NOT NULL DEFAULT 0"
        ),
        "dispatch_lane": "ALTER TABLE kairo_voice_log ADD COLUMN dispatch_lane TEXT",
        "action_tier": "ALTER TABLE kairo_voice_log ADD COLUMN action_tier TEXT",
        "voice_routing_mode": "ALTER TABLE kairo_voice_log ADD COLUMN voice_routing_mode TEXT",
        "model_receipt_json": "ALTER TABLE kairo_voice_log ADD COLUMN model_receipt_json TEXT",
    }
    for column, statement in migrations.items():
        if column not in columns:
            connection.execute(statement)


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
    dispatch_lane: str | None = None,
    action_tier: str | None = None,
    model_receipt: dict[str, Any] | None = None,
    voice_routing_mode: str | None = None,
) -> dict[str, str]:
    entry_id = f"voice_{uuid4().hex[:12]}"
    created_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    receipt_json = json.dumps(model_receipt) if model_receipt else None
    with _managed_connection() as connection:
        _ensure_voice_log_table(connection)
        connection.execute(
            """
            INSERT INTO kairo_voice_log (
                entry_id, created_at, session_id, workspace_id,
                raw_content, normalized_content, reply, turn_kind, source, stt_note,
                duration_ms, runtime_dispatched, dispatch_lane, action_tier,
                voice_routing_mode, model_receipt_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                dispatch_lane,
                action_tier,
                voice_routing_mode,
                receipt_json,
            ),
        )
        connection.commit()
    return {"entry_id": entry_id, "created_at": created_at}


def list_recent_voice_transcripts(
    *,
    limit: int = 20,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    capped = max(1, min(int(limit), 100))
    clean_session_id = str(session_id or "").strip()
    with _managed_connection() as connection:
        _ensure_voice_log_table(connection)
        if clean_session_id:
            rows = connection.execute(
                """
                SELECT entry_id, created_at, session_id, workspace_id,
                       raw_content, normalized_content, reply, turn_kind, source, stt_note,
                       duration_ms, runtime_dispatched, dispatch_lane, action_tier,
                       voice_routing_mode, model_receipt_json
                FROM kairo_voice_log
                WHERE session_id = ?
                ORDER BY created_at DESC, entry_id DESC
                LIMIT ?
                """,
                (clean_session_id, capped),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT entry_id, created_at, session_id, workspace_id,
                       raw_content, normalized_content, reply, turn_kind, source, stt_note,
                       duration_ms, runtime_dispatched, dispatch_lane, action_tier,
                       voice_routing_mode, model_receipt_json
                FROM kairo_voice_log
                ORDER BY created_at DESC, entry_id DESC
                LIMIT ?
                """,
                (capped,),
            ).fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        receipt_raw = item.pop("model_receipt_json", None)
        if receipt_raw:
            try:
                item["model_receipt"] = json.loads(str(receipt_raw))
            except json.JSONDecodeError:
                item["model_receipt"] = None
        else:
            item["model_receipt"] = None
        results.append(item)
    return results


def list_recent_spoken_lines(*, session_id: str, limit: int = 5) -> list[str]:
    clean_session_id = str(session_id or "").strip()
    if not clean_session_id:
        return []
    capped = max(1, min(int(limit), 20))
    with _managed_connection() as connection:
        _ensure_voice_log_table(connection)
        rows = connection.execute(
            """
            SELECT rowid, reply
            FROM kairo_voice_log
            WHERE session_id = ? AND TRIM(reply) <> ''
            ORDER BY rowid DESC
            LIMIT ?
            """,
            (clean_session_id, capped * 4),
        ).fetchall()
    lines: list[str] = []
    seen: set[str] = set()
    for row in rows:
        line = str(row["reply"] or "").strip()
        if not line:
            continue
        normalized = " ".join(line.lower().split())
        if normalized in seen:
            continue
        seen.add(normalized)
        lines.append(line)
        if len(lines) >= capped:
            break
    lines.reverse()
    return lines
