"""Durable Gate 9 CI event + open-signal store (SQLite beside control-plane DB)."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

_LOCK = threading.Lock()
_MEMORY_CONN: sqlite3.Connection | None = None


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _db_path() -> str | None:
    configured = os.environ.get("AXON_WATCH_CONTROL_PLANE_DB", "").strip()
    if not configured:
        return None
    path = Path(configured)
    return str(path.with_name(f"{path.stem}-ci-remediation{path.suffix or '.sqlite3'}"))


def _connect() -> sqlite3.Connection:
    global _MEMORY_CONN
    path = _db_path()
    if path is None:
        if _MEMORY_CONN is None:
            _MEMORY_CONN = sqlite3.connect(":memory:", check_same_thread=False)
            _MEMORY_CONN.row_factory = sqlite3.Row
            _ensure_schema(_MEMORY_CONN)
        return _MEMORY_CONN
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ci_remediation_events (
            dedupe_key TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            task_id TEXT,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ci_remediation_signals (
            signal_id TEXT PRIMARY KEY,
            dedupe_key TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            severity TEXT NOT NULL,
            status TEXT NOT NULL,
            html_url TEXT,
            meta_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.commit()


@contextmanager
def _managed() -> Iterator[sqlite3.Connection]:
    with _LOCK:
        conn = _connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if _db_path() is not None:
                conn.close()


def reset_store_for_tests() -> None:
    global _MEMORY_CONN
    with _LOCK:
        if _MEMORY_CONN is not None:
            _MEMORY_CONN.close()
            _MEMORY_CONN = None
        path = _db_path()
        if path and Path(path).is_file():
            Path(path).unlink(missing_ok=True)


def get_event(dedupe_key: str) -> dict[str, Any] | None:
    with _managed() as conn:
        row = conn.execute(
            "SELECT * FROM ci_remediation_events WHERE dedupe_key = ?",
            (dedupe_key,),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def upsert_open_event(
    *,
    dedupe_key: str,
    run_id: str,
    workspace_id: str,
    payload: dict[str, Any],
    task_id: str | None = None,
) -> dict[str, Any]:
    now = _utc_now_iso()
    with _managed() as conn:
        existing = conn.execute(
            "SELECT * FROM ci_remediation_events WHERE dedupe_key = ?",
            (dedupe_key,),
        ).fetchone()
        if existing is not None:
            status = str(existing["status"] or "")
            if status in {"open", "repairing"}:
                return dict(existing)
            # Re-open only when prior attempt exhausted or completed.
        conn.execute(
            """
            INSERT INTO ci_remediation_events (
                dedupe_key, run_id, workspace_id, task_id, payload_json,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'open', ?, ?)
            ON CONFLICT(dedupe_key) DO UPDATE SET
                run_id = excluded.run_id,
                workspace_id = excluded.workspace_id,
                task_id = COALESCE(excluded.task_id, ci_remediation_events.task_id),
                payload_json = excluded.payload_json,
                status = 'open',
                updated_at = excluded.updated_at
            """,
            (
                dedupe_key,
                run_id,
                workspace_id,
                task_id,
                json.dumps(payload),
                now,
                now,
            ),
        )
        row = conn.execute(
            "SELECT * FROM ci_remediation_events WHERE dedupe_key = ?",
            (dedupe_key,),
        ).fetchone()
    assert row is not None
    return dict(row)


def attach_task(dedupe_key: str, task_id: str, *, status: str = "repairing") -> None:
    now = _utc_now_iso()
    with _managed() as conn:
        conn.execute(
            """
            UPDATE ci_remediation_events
            SET task_id = ?, status = ?, updated_at = ?
            WHERE dedupe_key = ?
            """,
            (task_id, status, now, dedupe_key),
        )


def set_event_status(dedupe_key: str, status: str) -> None:
    now = _utc_now_iso()
    with _managed() as conn:
        conn.execute(
            """
            UPDATE ci_remediation_events
            SET status = ?, updated_at = ?
            WHERE dedupe_key = ?
            """,
            (status, now, dedupe_key),
        )


def upsert_signal(
    *,
    signal_id: str,
    dedupe_key: str,
    workspace_id: str,
    title: str,
    summary: str,
    severity: str,
    status: str,
    html_url: str = "",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = _utc_now_iso()
    meta_json = json.dumps(meta or {})
    with _managed() as conn:
        conn.execute(
            """
            INSERT INTO ci_remediation_signals (
                signal_id, dedupe_key, workspace_id, title, summary, severity,
                status, html_url, meta_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(signal_id) DO UPDATE SET
                title = excluded.title,
                summary = excluded.summary,
                severity = excluded.severity,
                status = excluded.status,
                html_url = excluded.html_url,
                meta_json = excluded.meta_json,
                updated_at = excluded.updated_at
            """,
            (
                signal_id,
                dedupe_key,
                workspace_id,
                title,
                summary,
                severity,
                status,
                html_url,
                meta_json,
                now,
                now,
            ),
        )
        row = conn.execute(
            "SELECT * FROM ci_remediation_signals WHERE signal_id = ?",
            (signal_id,),
        ).fetchone()
    assert row is not None
    return dict(row)


def list_open_signals() -> list[dict[str, Any]]:
    with _managed() as conn:
        rows = conn.execute(
            """
            SELECT * FROM ci_remediation_signals
            WHERE status IN ('open', 'repairing')
            ORDER BY updated_at DESC
            """
        ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        try:
            item["meta"] = json.loads(str(item.get("meta_json") or "{}"))
        except json.JSONDecodeError:
            item["meta"] = {}
        out.append(item)
    return out
