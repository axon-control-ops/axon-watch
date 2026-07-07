"""SQLite cache for research lookups."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone

from app.persistence.run_store_sqlite import connect, ensure_schema


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _ensure_research_cache(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS research_cache (
            cache_key TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
        """
    )
    connection.commit()


def _connection() -> sqlite3.Connection:
    connection = connect(None)
    ensure_schema(connection)
    _ensure_research_cache(connection)
    return connection


def _cache_key(kind: str, value: str) -> str:
    digest = hashlib.sha256(f"{kind}:{value}".encode("utf-8")).hexdigest()
    return digest


def get_cached(kind: str, value: str) -> dict[str, object] | None:
    key = _cache_key(kind, value)
    connection = _connection()
    row = connection.execute(
        "SELECT payload_json, expires_at FROM research_cache WHERE cache_key = ?",
        (key,),
    ).fetchone()
    connection.close()
    if row is None:
        return None
    expires_at = str(row["expires_at"])
    if expires_at <= _utc_now():
        return None
    payload = json.loads(str(row["payload_json"]))
    return payload if isinstance(payload, dict) else None


def set_cached(kind: str, value: str, payload: dict[str, object], *, ttl_hours: int = 24) -> None:
    key = _cache_key(kind, value)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=max(1, ttl_hours))
    connection = _connection()
    connection.execute(
        """
        INSERT INTO research_cache(cache_key, kind, payload_json, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(cache_key) DO UPDATE SET
            payload_json = excluded.payload_json,
            created_at = excluded.created_at,
            expires_at = excluded.expires_at
        """,
        (
            key,
            kind,
            json.dumps(payload),
            now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            expires.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        ),
    )
    connection.commit()
    connection.close()
