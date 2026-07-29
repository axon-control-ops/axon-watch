"""Persisted autonomy attend decisions and action receipts."""

from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.persistence import run_store_sqlite

_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|APIKEY))"
    r"\s*([:=])\s*([^\s,;]+)"
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_KNOWN_TOKEN_RE = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})\b")
_SENSITIVE_KEY_RE = re.compile(
    r"(?i)(token|secret|password|api[_-]?key|authorization|credential)"
)


def _redact_text(value: Any) -> str:
    text = str(value or "")
    text = _SECRET_ASSIGNMENT_RE.sub(r"\1\2[REDACTED]", text)
    text = _BEARER_RE.sub("Bearer [REDACTED]", text)
    return _KNOWN_TOKEN_RE.sub("[REDACTED]", text)


def _redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): (
                "[REDACTED]"
                if _SENSITIVE_KEY_RE.search(str(key))
                else _redact_payload(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_payload(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value

_RECEIPT_COLUMNS = (
    "receipt_id",
    "workspace_id",
    "kind",
    "decision",
    "tier",
    "risk",
    "title",
    "detail",
    "dedupe_key",
    "task_id",
    "ask_operator",
    "status",
    "resolution",
    "resolved_at",
    "payload_json",
    "created_at",
)


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
    from datetime import datetime, timezone

    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def ensure_autonomy_receipt_schema(connection: Any) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS autonomy_attention_receipts (
            receipt_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL DEFAULT '',
            kind TEXT NOT NULL,
            decision TEXT NOT NULL,
            tier TEXT NOT NULL,
            risk TEXT NOT NULL DEFAULT 'normal',
            title TEXT NOT NULL DEFAULT '',
            detail TEXT NOT NULL DEFAULT '',
            dedupe_key TEXT NOT NULL DEFAULT '',
            task_id TEXT,
            ask_operator INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'recorded',
            resolution TEXT NOT NULL DEFAULT '',
            resolved_at TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
    )
    columns = {
        str(row["name"])
        for row in connection.execute(
            "PRAGMA table_info(autonomy_attention_receipts)"
        ).fetchall()
    }
    optional = (
        ("status", "TEXT NOT NULL DEFAULT 'recorded'"),
        ("resolution", "TEXT NOT NULL DEFAULT ''"),
        ("resolved_at", "TEXT"),
    )
    for name, ddl in optional:
        if name not in columns:
            connection.execute(
                f"ALTER TABLE autonomy_attention_receipts ADD COLUMN {name} {ddl}"
            )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_autonomy_receipts_created
            ON autonomy_attention_receipts(created_at DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_autonomy_receipts_dedupe
            ON autonomy_attention_receipts(dedupe_key, created_at DESC)
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS autonomy_attention_meta (
            meta_key TEXT PRIMARY KEY,
            meta_value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )


def _row_to_record(row: Any) -> dict[str, Any]:
    try:
        payload = json.loads(row["payload_json"] or "{}")
    except (TypeError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    return {
        "receipt_id": row["receipt_id"],
        "workspace_id": row["workspace_id"] or "",
        "kind": row["kind"],
        "decision": row["decision"],
        "tier": row["tier"],
        "risk": row["risk"] or "normal",
        "title": row["title"] or "",
        "detail": row["detail"] or "",
        "dedupe_key": row["dedupe_key"] or "",
        "task_id": row["task_id"],
        "ask_operator": bool(row["ask_operator"]),
        "status": row["status"] or "recorded",
        "resolution": row["resolution"] or "",
        "resolved_at": row["resolved_at"],
        "payload": payload,
        "created_at": row["created_at"],
    }


def reset_store() -> None:
    with _managed_connection() as connection:
        ensure_autonomy_receipt_schema(connection)
        connection.execute("DELETE FROM autonomy_attention_receipts")
        connection.execute("DELETE FROM autonomy_attention_meta")
        connection.commit()


def set_meta(key: str, value: Any) -> None:
    cleaned = str(key or "").strip()
    if not cleaned:
        return
    stamp = _utc_now_iso()
    serialized = json.dumps(value)
    with _managed_connection() as connection:
        ensure_autonomy_receipt_schema(connection)
        connection.execute(
            """
            INSERT INTO autonomy_attention_meta (meta_key, meta_value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(meta_key) DO UPDATE SET
                meta_value = excluded.meta_value,
                updated_at = excluded.updated_at
            """,
            (cleaned, serialized, stamp),
        )
        connection.commit()


def get_meta(key: str, default: Any = None) -> Any:
    cleaned = str(key or "").strip()
    if not cleaned:
        return default
    with _managed_connection() as connection:
        ensure_autonomy_receipt_schema(connection)
        row = connection.execute(
            "SELECT meta_value FROM autonomy_attention_meta WHERE meta_key = ?",
            (cleaned,),
        ).fetchone()
    if row is None:
        return default
    try:
        return json.loads(row["meta_value"])
    except (TypeError, json.JSONDecodeError):
        return default


def append_receipt(
    *,
    kind: str,
    decision: str,
    tier: str,
    risk: str = "normal",
    title: str = "",
    detail: str = "",
    dedupe_key: str = "",
    workspace_id: str = "",
    task_id: str | None = None,
    ask_operator: bool = False,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stamp = _utc_now_iso()
    record = {
        "receipt_id": f"auton-{uuid.uuid4().hex[:16]}",
        "workspace_id": str(workspace_id or "").strip(),
        "kind": str(kind or "attention").strip() or "attention",
        "decision": str(decision or "skip").strip() or "skip",
        "tier": str(tier or "unclassified").strip() or "unclassified",
        "risk": str(risk or "normal").strip() or "normal",
        "title": _redact_text(title).strip()[:240],
        "detail": _redact_text(detail).strip()[:500],
        "dedupe_key": _redact_text(dedupe_key).strip()[:240],
        "task_id": (str(task_id).strip() if task_id else None),
        "ask_operator": 1 if ask_operator else 0,
        "status": "pending" if ask_operator else "recorded",
        "resolution": "",
        "resolved_at": None,
        "payload_json": json.dumps(_redact_payload(payload or {})),
        "created_at": stamp,
    }
    with _managed_connection() as connection:
        ensure_autonomy_receipt_schema(connection)
        placeholders = ", ".join("?" for _ in _RECEIPT_COLUMNS)
        connection.execute(
            f"""
            INSERT INTO autonomy_attention_receipts ({", ".join(_RECEIPT_COLUMNS)})
            VALUES ({placeholders})
            """,
            tuple(record[column] for column in _RECEIPT_COLUMNS),
        )
        connection.commit()
    stored = {
        **{key: record[key] for key in _RECEIPT_COLUMNS if key != "payload_json"},
        "ask_operator": bool(record["ask_operator"]),
        "payload": _redact_payload(payload or {}),
    }
    return deepcopy(stored)


def get_receipt(receipt_id: str) -> dict[str, Any] | None:
    cleaned = str(receipt_id or "").strip()
    if not cleaned:
        return None
    with _managed_connection() as connection:
        ensure_autonomy_receipt_schema(connection)
        row = connection.execute(
            "SELECT * FROM autonomy_attention_receipts WHERE receipt_id = ?",
            (cleaned,),
        ).fetchone()
    return _row_to_record(row) if row is not None else None


def list_receipts(
    *,
    limit: int = 40,
    ask_operator_only: bool = False,
    status: str | None = None,
    workspace_id: str | None = None,
) -> list[dict[str, Any]]:
    bound = max(1, min(500, int(limit or 40)))
    status_filter = str(status or "").strip().lower()
    workspace_filter = str(workspace_id or "").strip()
    conditions: list[str] = []
    params: list[Any] = []
    if ask_operator_only:
        conditions.append("ask_operator = 1")
    if status_filter:
        conditions.append("status = ?")
        params.append(status_filter)
    if workspace_filter:
        conditions.append("workspace_id = ?")
        params.append(workspace_filter)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with _managed_connection() as connection:
        ensure_autonomy_receipt_schema(connection)
        rows = connection.execute(
            f"""
            SELECT * FROM autonomy_attention_receipts
            {where}
            ORDER BY created_at DESC, receipt_id ASC
            LIMIT ?
            """,
            (*params, bound),
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def list_pending_decisions(
    *,
    limit: int = 100,
    workspace_id: str | None = None,
) -> list[dict[str, Any]]:
    return list_receipts(
        limit=limit,
        ask_operator_only=True,
        status="pending",
        workspace_id=workspace_id,
    )


def begin_decision_resolution(receipt_id: str) -> dict[str, Any]:
    """Atomically reserve a pending decision before creating any task."""
    cleaned = str(receipt_id or "").strip()
    current = get_receipt(cleaned)
    if current is None:
        raise ValueError(f"autonomy decision not found: {cleaned}")
    if current.get("status") != "pending":
        raise ValueError(f"autonomy decision already resolving or resolved: {cleaned}")
    with _managed_connection() as connection:
        ensure_autonomy_receipt_schema(connection)
        cursor = connection.execute(
            """
            UPDATE autonomy_attention_receipts
            SET status = 'resolving'
            WHERE receipt_id = ? AND status = 'pending'
            """,
            (cleaned,),
        )
        if cursor.rowcount != 1:
            connection.rollback()
            raise ValueError(f"autonomy decision changed concurrently: {cleaned}")
        connection.commit()
    claimed = get_receipt(cleaned)
    assert claimed is not None
    return claimed


def complete_decision_resolution(
    receipt_id: str,
    *,
    resolution: str,
    task_id: str | None = None,
) -> dict[str, Any]:
    cleaned = str(receipt_id or "").strip()
    choice = str(resolution or "").strip().lower()
    if choice not in {"approved", "rejected"}:
        raise ValueError("resolution must be approved or rejected")
    stamp = _utc_now_iso()
    with _managed_connection() as connection:
        ensure_autonomy_receipt_schema(connection)
        cursor = connection.execute(
            """
            UPDATE autonomy_attention_receipts
            SET status = 'resolved',
                resolution = ?,
                resolved_at = ?,
                task_id = COALESCE(?, task_id)
            WHERE receipt_id = ? AND status = 'resolving'
            """,
            (choice, stamp, (str(task_id).strip() if task_id else None), cleaned),
        )
        if cursor.rowcount != 1:
            connection.rollback()
            raise ValueError(f"autonomy decision changed concurrently: {cleaned}")
        connection.commit()
    resolved = get_receipt(cleaned)
    assert resolved is not None
    return resolved


def release_decision_resolution(receipt_id: str) -> None:
    """Return a failed resolution attempt to pending."""
    cleaned = str(receipt_id or "").strip()
    if not cleaned:
        return
    with _managed_connection() as connection:
        ensure_autonomy_receipt_schema(connection)
        connection.execute(
            """
            UPDATE autonomy_attention_receipts
            SET status = 'pending'
            WHERE receipt_id = ? AND status = 'resolving'
            """,
            (cleaned,),
        )
        connection.commit()


def resolve_decision(
    receipt_id: str,
    *,
    resolution: str,
    task_id: str | None = None,
) -> dict[str, Any]:
    begin_decision_resolution(receipt_id)
    try:
        return complete_decision_resolution(
            receipt_id,
            resolution=resolution,
            task_id=task_id,
        )
    except Exception:
        release_decision_resolution(receipt_id)
        raise


def has_recent_dedupe_key(
    dedupe_key: str,
    *,
    cooldown_seconds: int = 900,
) -> bool:
    key = str(dedupe_key or "").strip()
    if not key:
        return False
    pending = list_pending_decisions(limit=500)
    if any(str(row.get("dedupe_key") or "") == key for row in pending):
        return True
    resolving = list_receipts(limit=500, status="resolving")
    if any(str(row.get("dedupe_key") or "") == key for row in resolving):
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(
        seconds=max(1, int(cooldown_seconds))
    )
    for row in list_receipts(limit=500):
        if str(row.get("dedupe_key") or "") != key:
            continue
        raw = str(row.get("resolved_at") or row.get("created_at") or "").replace(
            "Z", "+00:00"
        )
        try:
            created = datetime.fromisoformat(raw)
        except ValueError:
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created.astimezone(timezone.utc) >= cutoff:
            return True
    return False


__all__ = [
    "append_receipt",
    "begin_decision_resolution",
    "complete_decision_resolution",
    "ensure_autonomy_receipt_schema",
    "get_receipt",
    "get_meta",
    "has_recent_dedupe_key",
    "list_pending_decisions",
    "list_receipts",
    "release_decision_resolution",
    "resolve_decision",
    "reset_store",
    "set_meta",
]
