"""Durable VAXON fleet self-heal event + signal store (SQLite beside control-plane DB).

Sidecar to the main control-plane DB, mirroring app/ci_remediation/store.py's
shape exactly — separate ownership, separate lifecycle, same reasoning: this
is fleet-repair bookkeeping, not user/workspace data.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.persistence.sqlite_connection import ManagedConnection

_LOCK = threading.Lock()
_MEMORY_CONN: sqlite3.Connection | None = None
_MAX_SAMPLE_ITEMS = 8

_OPEN_SIGNAL_STATUSES = ("open", "repairing")


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
    return str(path.with_name(f"{path.stem}-fleet-self-heal{path.suffix or '.sqlite3'}"))


def _connect() -> sqlite3.Connection:
    global _MEMORY_CONN
    path = _db_path()
    if path is None:
        if _MEMORY_CONN is None:
            _MEMORY_CONN = sqlite3.connect(
                ":memory:", check_same_thread=False, factory=ManagedConnection
            )
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
        CREATE TABLE IF NOT EXISTS fleet_repair_events (
            fingerprint TEXT PRIMARY KEY,
            subsystem TEXT NOT NULL,
            file_hint TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            task_id TEXT,
            occurrence_count INTEGER NOT NULL DEFAULT 0,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            workspaces_json TEXT NOT NULL DEFAULT '[]',
            roles_json TEXT NOT NULL DEFAULT '[]',
            sample_run_ids_json TEXT NOT NULL DEFAULT '[]',
            attempts_used INTEGER NOT NULL DEFAULT 0,
            lifetime_dispatch_count INTEGER NOT NULL DEFAULT 0,
            resolution_commit_ref TEXT,
            resolution_verified_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS fleet_repair_signals (
            signal_id TEXT PRIMARY KEY,
            fingerprint TEXT NOT NULL,
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


def _row_to_event(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    for key in ("workspaces_json", "roles_json", "sample_run_ids_json"):
        raw = str(item.get(key) or "[]")
        try:
            item[key] = json.loads(raw)
        except json.JSONDecodeError:
            item[key] = []
    return item


def get_event(fingerprint: str) -> dict[str, Any] | None:
    with _managed() as conn:
        row = conn.execute(
            "SELECT * FROM fleet_repair_events WHERE fingerprint = ?",
            (fingerprint,),
        ).fetchone()
    if row is None:
        return None
    return _row_to_event(row)


def _capped_unique(existing: list[Any], addition: Any) -> list[Any]:
    items = [item for item in existing if item != addition]
    items.append(addition)
    return items[-_MAX_SAMPLE_ITEMS:]


def upsert_observation(
    fingerprint: str,
    *,
    subsystem: str,
    file_hint: str,
    workspace_id: str,
    role: str,
    run_id: str,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Record one occurrence of a failure signature, creating the event if new.

    ``observed_at`` should be the failing run's own timestamp (e.g. its
    ``updated_at``), not wall-clock processing time — a scanner working
    through a backlog must not treat an old failure as fresh just because it
    was processed just now, or staleness/recency pruning breaks silently.
    """
    now = _utc_now_iso()
    occurred_at = observed_at or now
    with _managed() as conn:
        existing = conn.execute(
            "SELECT * FROM fleet_repair_events WHERE fingerprint = ?",
            (fingerprint,),
        ).fetchone()
        if existing is None:
            conn.execute(
                """
                INSERT INTO fleet_repair_events (
                    fingerprint, subsystem, file_hint, status, occurrence_count,
                    first_seen_at, last_seen_at, workspaces_json, roles_json,
                    sample_run_ids_json, created_at, updated_at
                ) VALUES (?, ?, ?, 'observed', 1, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fingerprint,
                    subsystem,
                    file_hint,
                    occurred_at,
                    occurred_at,
                    json.dumps([workspace_id]),
                    json.dumps([role]),
                    json.dumps([run_id]),
                    now,
                    now,
                ),
            )
        else:
            prior = _row_to_event(existing)
            workspaces = _capped_unique(prior["workspaces_json"], workspace_id)
            roles = _capped_unique(prior["roles_json"], role)
            run_ids = _capped_unique(prior["sample_run_ids_json"], run_id)
            prior_last_seen = str(prior.get("last_seen_at") or "")
            new_last_seen = occurred_at if occurred_at > prior_last_seen else prior_last_seen
            conn.execute(
                """
                UPDATE fleet_repair_events
                SET occurrence_count = occurrence_count + 1,
                    last_seen_at = ?,
                    workspaces_json = ?,
                    roles_json = ?,
                    sample_run_ids_json = ?,
                    updated_at = ?
                WHERE fingerprint = ?
                """,
                (
                    new_last_seen,
                    json.dumps(workspaces),
                    json.dumps(roles),
                    json.dumps(run_ids),
                    now,
                    fingerprint,
                ),
            )
        row = conn.execute(
            "SELECT * FROM fleet_repair_events WHERE fingerprint = ?",
            (fingerprint,),
        ).fetchone()
    assert row is not None
    return _row_to_event(row)


def attach_task(fingerprint: str, task_id: str, *, status: str = "repairing") -> None:
    now = _utc_now_iso()
    with _managed() as conn:
        conn.execute(
            """
            UPDATE fleet_repair_events
            SET task_id = ?, status = ?, lifetime_dispatch_count = lifetime_dispatch_count + 1,
                updated_at = ?
            WHERE fingerprint = ?
            """,
            (task_id, status, now, fingerprint),
        )


def set_event_status(fingerprint: str, status: str) -> None:
    now = _utc_now_iso()
    with _managed() as conn:
        conn.execute(
            "UPDATE fleet_repair_events SET status = ?, updated_at = ? WHERE fingerprint = ?",
            (status, now, fingerprint),
        )


def bump_attempts(fingerprint: str) -> int:
    """Increment attempts_used and return the new value."""
    now = _utc_now_iso()
    with _managed() as conn:
        conn.execute(
            """
            UPDATE fleet_repair_events
            SET attempts_used = attempts_used + 1, updated_at = ?
            WHERE fingerprint = ?
            """,
            (now, fingerprint),
        )
        row = conn.execute(
            "SELECT attempts_used FROM fleet_repair_events WHERE fingerprint = ?",
            (fingerprint,),
        ).fetchone()
    return int(row["attempts_used"]) if row is not None else 0


def record_verified_fix(fingerprint: str, *, commit_ref: str, verified_at: str | None = None) -> None:
    now = verified_at or _utc_now_iso()
    with _managed() as conn:
        conn.execute(
            """
            UPDATE fleet_repair_events
            SET status = 'verified_fixed', attempts_used = 0,
                resolution_commit_ref = ?, resolution_verified_at = ?, updated_at = ?
            WHERE fingerprint = ?
            """,
            (commit_ref, now, _utc_now_iso(), fingerprint),
        )


def list_open_signals() -> list[dict[str, Any]]:
    placeholders = ",".join("?" for _ in _OPEN_SIGNAL_STATUSES)
    with _managed() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM fleet_repair_signals
            WHERE status IN ({placeholders})
            ORDER BY updated_at DESC
            """,
            _OPEN_SIGNAL_STATUSES,
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


def upsert_signal(
    *,
    signal_id: str,
    fingerprint: str,
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
            INSERT INTO fleet_repair_signals (
                signal_id, fingerprint, workspace_id, title, summary, severity,
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
                fingerprint,
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
            "SELECT * FROM fleet_repair_signals WHERE signal_id = ?",
            (signal_id,),
        ).fetchone()
    assert row is not None
    return dict(row)


def resolve_signal(
    signal_id: str,
    *,
    reason: str = "verified_fixed",
    status: str = "resolved",
) -> dict[str, Any] | None:
    cleaned = str(signal_id or "").strip()
    if not cleaned:
        return None
    now = _utc_now_iso()
    with _managed() as conn:
        row = conn.execute(
            "SELECT * FROM fleet_repair_signals WHERE signal_id = ?",
            (cleaned,),
        ).fetchone()
        if row is None:
            return None
        meta: dict[str, Any]
        try:
            meta = json.loads(str(row["meta_json"] or "{}"))
        except json.JSONDecodeError:
            meta = {}
        if not isinstance(meta, dict):
            meta = {}
        meta["resolved_reason"] = str(reason or "verified_fixed").strip() or "verified_fixed"
        conn.execute(
            """
            UPDATE fleet_repair_signals
            SET status = ?, meta_json = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, json.dumps(meta), now, cleaned),
        )
        updated = conn.execute(
            "SELECT * FROM fleet_repair_signals WHERE signal_id = ?",
            (cleaned,),
        ).fetchone()
    if updated is None:
        return None
    item = dict(updated)
    try:
        item["meta"] = json.loads(str(item.get("meta_json") or "{}"))
    except json.JSONDecodeError:
        item["meta"] = {}
    return item


def known_blocked_signal_for(workspace_id: str, role: str) -> str | None:
    """Informational lookup for scheduler_auto_start_gates: is this role's
    current backoff actually a known, already-diagnosed fleet bug?"""
    with _managed() as conn:
        rows = conn.execute(
            "SELECT fingerprint, status, workspaces_json, roles_json FROM fleet_repair_events "
            "WHERE status IN ('dispatched', 'repairing', 'blocked')"
        ).fetchall()
    for row in rows:
        try:
            workspaces = json.loads(str(row["workspaces_json"] or "[]"))
            roles = json.loads(str(row["roles_json"] or "[]"))
        except json.JSONDecodeError:
            continue
        if workspace_id in workspaces and role in roles:
            status = str(row["status"] or "")
            return f"{row['fingerprint']}: {status}, VAXON fleet-repair in progress"
    return None
