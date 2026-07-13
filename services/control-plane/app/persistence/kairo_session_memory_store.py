"""SQLite persistence for KAIRO session turn and entity memory (M2)."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from app.persistence import run_store_sqlite

_MAX_SESSION_BYTES = 16 * 1024


def _configured_db_path() -> str | None:
    return os.environ.get("AXON_WATCH_CONTROL_PLANE_DB")


@contextmanager
def _managed_connection():
    connection = run_store_sqlite.connect(_configured_db_path())
    try:
        yield connection
    finally:
        connection.close()


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _trim_to_byte_cap(turns: list[dict[str, str]], entities: dict[str, str]) -> tuple[list[dict[str, str]], dict[str, str]]:
    trimmed_turns = list(turns)
    trimmed_entities = dict(entities)
    while True:
        payload = json.dumps(
            {"turns": trimmed_turns, "entities": trimmed_entities},
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if len(payload) <= _MAX_SESSION_BYTES:
            return trimmed_turns, trimmed_entities
        if trimmed_turns:
            trimmed_turns.pop(0)
            continue
        if trimmed_entities:
            oldest_key = next(iter(sorted(trimmed_entities)))
            del trimmed_entities[oldest_key]
            continue
        return trimmed_turns, trimmed_entities


def load_session_memory(session_key: str) -> tuple[list[dict[str, str]], dict[str, str]] | None:
    with _managed_connection() as connection:
        row = connection.execute(
            """
            SELECT turns_json, entities_json
            FROM kairo_session_memory
            WHERE session_key = ?
            """,
            (session_key,),
        ).fetchone()
    if row is None:
        return None
    turns = json.loads(row["turns_json"] or "[]")
    entities = json.loads(row["entities_json"] or "{}")
    if not isinstance(turns, list):
        turns = []
    if not isinstance(entities, dict):
        entities = {}
    normalized_turns = [
        {"role": str(item.get("role") or ""), "content": str(item.get("content") or "")}
        for item in turns
        if isinstance(item, dict)
    ]
    normalized_entities = {
        str(key): str(value)
        for key, value in entities.items()
        if str(value or "").strip()
    }
    return normalized_turns, normalized_entities


def save_session_memory(
    session_key: str,
    turns: list[dict[str, str]],
    entities: dict[str, str],
) -> None:
    trimmed_turns, trimmed_entities = _trim_to_byte_cap(list(turns), dict(entities))
    turns_json = json.dumps(trimmed_turns, separators=(",", ":"), sort_keys=True)
    entities_json = json.dumps(trimmed_entities, separators=(",", ":"), sort_keys=True)
    updated_at = _utc_now()
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO kairo_session_memory (session_key, turns_json, entities_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_key) DO UPDATE SET
                turns_json = excluded.turns_json,
                entities_json = excluded.entities_json,
                updated_at = excluded.updated_at
            """,
            (session_key, turns_json, entities_json, updated_at),
        )
        connection.commit()


def delete_all_session_memory_for_tests() -> None:
    with _managed_connection() as connection:
        connection.execute("DELETE FROM kairo_session_memory")
        connection.commit()


__all__ = [
    "delete_all_session_memory_for_tests",
    "load_session_memory",
    "save_session_memory",
]
