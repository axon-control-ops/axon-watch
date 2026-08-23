"""Durable recovery records, checkpoints, circuits, and retry fingerprints."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.persistence.sqlite_connection import ManagedConnection
from app.platform_recovery.states import normalize_bucket, normalize_failure_class

_LOCK = threading.Lock()
_MEMORY_CONN: sqlite3.Connection | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _db_path() -> str | None:
    configured = os.environ.get("AXON_WATCH_CONTROL_PLANE_DB", "").strip()
    if not configured:
        return None
    path = Path(configured)
    return str(path.with_name(f"{path.stem}-recovery{path.suffix or '.sqlite3'}"))


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
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS recovery_records (
            recovery_id TEXT PRIMARY KEY,
            run_id TEXT,
            task_id TEXT,
            workspace_id TEXT NOT NULL DEFAULT '',
            bucket TEXT NOT NULL,
            failure_class TEXT NOT NULL,
            recovery_state TEXT NOT NULL,
            what_happened TEXT NOT NULL DEFAULT '',
            why_stale TEXT NOT NULL DEFAULT '',
            next_action TEXT NOT NULL DEFAULT '',
            evidence_json TEXT NOT NULL DEFAULT '{}',
            acknowledged INTEGER NOT NULL DEFAULT 0,
            idempotency_key TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS recovery_records_idempotency
            ON recovery_records(idempotency_key) WHERE idempotency_key IS NOT NULL;
        CREATE TABLE IF NOT EXISTS run_checkpoints (
            run_id TEXT PRIMARY KEY,
            mission_id TEXT NOT NULL DEFAULT '',
            task_id TEXT NOT NULL DEFAULT '',
            worker_id TEXT NOT NULL DEFAULT '',
            workspace_id TEXT NOT NULL DEFAULT '',
            branch TEXT NOT NULL DEFAULT '',
            worktree TEXT NOT NULL DEFAULT '',
            current_stage TEXT NOT NULL DEFAULT '',
            last_verified_stage TEXT NOT NULL DEFAULT '',
            last_checkpoint_at TEXT NOT NULL,
            last_meaningful_progress_at TEXT NOT NULL DEFAULT '',
            attempt_number INTEGER NOT NULL DEFAULT 1,
            remaining_attempt_budget INTEGER NOT NULL DEFAULT 0,
            execution_provider TEXT NOT NULL DEFAULT '',
            execution_context_reference TEXT NOT NULL DEFAULT '',
            changed_paths_json TEXT NOT NULL DEFAULT '[]',
            verification_state TEXT NOT NULL DEFAULT '',
            recovery_state TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS circuit_breakers (
            name TEXT PRIMARY KEY,
            state TEXT NOT NULL DEFAULT 'CLOSED',
            failure_count INTEGER NOT NULL DEFAULT 0,
            opened_at TEXT,
            last_failure_at TEXT,
            last_success_at TEXT
        );
        CREATE TABLE IF NOT EXISTS retry_fingerprints (
            fingerprint TEXT PRIMARY KEY,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            last_action TEXT NOT NULL DEFAULT '',
            last_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS recovery_lessons (
            lesson_id TEXT PRIMARY KEY,
            failure_class TEXT NOT NULL,
            root_cause TEXT NOT NULL DEFAULT '',
            recovery TEXT NOT NULL DEFAULT '',
            verification TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT 'low',
            provenance_run_id TEXT NOT NULL DEFAULT '',
            verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """
    )
    connection.commit()


@contextmanager
def _managed() -> Iterator[sqlite3.Connection]:
    with _LOCK:
        conn = _connect()
        try:
            yield conn
        finally:
            if _db_path() is not None:
                conn.close()


def reset_store() -> None:
    global _MEMORY_CONN
    with _LOCK:
        if _MEMORY_CONN is not None:
            _MEMORY_CONN.close()
            _MEMORY_CONN = None


def upsert_recovery_record(payload: dict[str, Any]) -> dict[str, Any]:
    now = _utc_now_iso()
    key = str(payload.get("idempotency_key") or "").strip() or None
    run_id = str(payload.get("run_id") or "").strip() or None
    with _managed() as conn:
        existing = None
        if key:
            existing = conn.execute(
                "SELECT * FROM recovery_records WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
        # Migrate older run:<id>:<bucket> rows to one stable per-run record.
        if existing is None and run_id and key == f"run:{run_id}":
            existing = conn.execute(
                """
                SELECT * FROM recovery_records
                WHERE run_id = ?
                ORDER BY acknowledged DESC, updated_at DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
        if existing is not None:
            conn.execute(
                """
                UPDATE recovery_records
                SET task_id = ?, workspace_id = ?, bucket = ?,
                    failure_class = ?, recovery_state = ?, what_happened = ?,
                    why_stale = ?, next_action = ?, evidence_json = ?,
                    idempotency_key = ?, updated_at = ?
                WHERE recovery_id = ?
                """,
                (
                    str(payload.get("task_id") or "") or None,
                    str(payload.get("workspace_id") or ""),
                    normalize_bucket(str(payload.get("bucket") or "HUMAN_REVIEW")),
                    normalize_failure_class(str(payload.get("failure_class") or "UNKNOWN")),
                    str(payload.get("recovery_state") or payload.get("bucket") or "HUMAN_REVIEW"),
                    str(payload.get("what_happened") or ""),
                    str(payload.get("why_stale") or ""),
                    str(payload.get("next_action") or ""),
                    json.dumps(payload.get("evidence") or {}, separators=(",", ":")),
                    key,
                    now,
                    existing["recovery_id"],
                ),
            )
            conn.commit()
            refreshed = conn.execute(
                "SELECT * FROM recovery_records WHERE recovery_id = ?",
                (existing["recovery_id"],),
            ).fetchone()
            return _recovery_row(refreshed)
        recovery_id = str(payload.get("recovery_id") or f"recovery_{uuid.uuid4().hex[:12]}")
        conn.execute(
            """
            INSERT INTO recovery_records (
                recovery_id, run_id, task_id, workspace_id, bucket, failure_class,
                recovery_state, what_happened, why_stale, next_action, evidence_json,
                acknowledged, idempotency_key, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(recovery_id) DO UPDATE SET
                bucket=excluded.bucket,
                failure_class=excluded.failure_class,
                recovery_state=excluded.recovery_state,
                what_happened=excluded.what_happened,
                why_stale=excluded.why_stale,
                next_action=excluded.next_action,
                evidence_json=excluded.evidence_json,
                updated_at=excluded.updated_at
            """,
            (
                recovery_id,
                run_id,
                str(payload.get("task_id") or "") or None,
                str(payload.get("workspace_id") or ""),
                normalize_bucket(str(payload.get("bucket") or "HUMAN_REVIEW")),
                normalize_failure_class(str(payload.get("failure_class") or "UNKNOWN")),
                str(payload.get("recovery_state") or payload.get("bucket") or "HUMAN_REVIEW"),
                str(payload.get("what_happened") or ""),
                str(payload.get("why_stale") or ""),
                str(payload.get("next_action") or ""),
                json.dumps(payload.get("evidence") or {}, separators=(",", ":")),
                1 if payload.get("acknowledged") else 0,
                key,
                str(payload.get("created_at") or now),
                now,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM recovery_records WHERE recovery_id = ?",
            (recovery_id,),
        ).fetchone()
    return _recovery_row(row)


def acknowledge_recovery(recovery_id: str) -> dict[str, Any] | None:
    with _managed() as conn:
        conn.execute(
            "UPDATE recovery_records SET acknowledged = 1, updated_at = ? WHERE recovery_id = ?",
            (_utc_now_iso(), recovery_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM recovery_records WHERE recovery_id = ?",
            (recovery_id,),
        ).fetchone()
    return _recovery_row(row) if row else None


def list_recovery_records(*, include_acknowledged: bool = False) -> list[dict[str, Any]]:
    sql = "SELECT * FROM recovery_records"
    if not include_acknowledged:
        sql += " WHERE acknowledged = 0"
    sql += " ORDER BY updated_at DESC"
    with _managed() as conn:
        rows = conn.execute(sql).fetchall()
    return [_recovery_row(row) for row in rows]


def _recovery_row(row: sqlite3.Row) -> dict[str, Any]:
    evidence = {}
    try:
        parsed = json.loads(str(row["evidence_json"] or "{}"))
        if isinstance(parsed, dict):
            evidence = parsed
    except json.JSONDecodeError:
        evidence = {}
    return {
        "recovery_id": row["recovery_id"],
        "run_id": row["run_id"],
        "task_id": row["task_id"],
        "workspace_id": row["workspace_id"],
        "bucket": row["bucket"],
        "failure_class": row["failure_class"],
        "recovery_state": row["recovery_state"],
        "what_happened": row["what_happened"],
        "why_stale": row["why_stale"],
        "next_action": row["next_action"],
        "evidence": evidence,
        "acknowledged": bool(row["acknowledged"]),
        "idempotency_key": row["idempotency_key"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def managed_connection():
    return _managed()


def utc_now_iso() -> str:
    return _utc_now_iso()
