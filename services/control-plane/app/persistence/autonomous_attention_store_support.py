"""Schema, row mapping, connection, and redaction helpers for autonomy attention."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
import re
from typing import Any, Iterator

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

RECEIPT_COLUMNS = (
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


def configured_db_path() -> str | None:
    return os.environ.get("AXON_WATCH_CONTROL_PLANE_DB")


def connection():
    return run_store_sqlite.connect(configured_db_path())


@contextmanager
def managed_connection() -> Iterator[Any]:
    conn = connection()
    try:
        yield conn
    finally:
        conn.close()


def utc_now_iso() -> str:
    from datetime import datetime, timezone

    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def redact_text(value: Any) -> str:
    text = str(value or "")
    text = _SECRET_ASSIGNMENT_RE.sub(r"\1\2[REDACTED]", text)
    text = _BEARER_RE.sub("Bearer [REDACTED]", text)
    return _KNOWN_TOKEN_RE.sub("[REDACTED]", text)


def redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): (
                "[REDACTED]"
                if _SENSITIVE_KEY_RE.search(str(key))
                else redact_payload(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    if isinstance(value, tuple):
        return [redact_payload(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


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


def row_to_record(row: Any) -> dict[str, Any]:
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


__all__ = [
    "RECEIPT_COLUMNS",
    "configured_db_path",
    "connection",
    "ensure_autonomy_receipt_schema",
    "managed_connection",
    "redact_payload",
    "redact_text",
    "row_to_record",
    "utc_now_iso",
]
