"""Persisted autonomy attend decisions and action receipts."""

from __future__ import annotations

from copy import deepcopy
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.persistence.autonomous_attention_store_support import (
    RECEIPT_COLUMNS,
    ensure_autonomy_receipt_schema,
    managed_connection,
    redact_payload,
    redact_text,
    row_to_record,
    utc_now_iso,
)


def reset_store() -> None:
    with managed_connection() as connection:
        ensure_autonomy_receipt_schema(connection)
        connection.execute("DELETE FROM autonomy_attention_receipts")
        connection.execute("DELETE FROM autonomy_attention_meta")
        connection.commit()


def set_meta(key: str, value: Any) -> None:
    cleaned = str(key or "").strip()
    if not cleaned:
        return
    stamp = utc_now_iso()
    serialized = json.dumps(value)
    with managed_connection() as connection:
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
    with managed_connection() as connection:
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
    stamp = utc_now_iso()
    record = {
        "receipt_id": f"auton-{uuid.uuid4().hex[:16]}",
        "workspace_id": str(workspace_id or "").strip(),
        "kind": str(kind or "attention").strip() or "attention",
        "decision": str(decision or "skip").strip() or "skip",
        "tier": str(tier or "unclassified").strip() or "unclassified",
        "risk": str(risk or "normal").strip() or "normal",
        "title": redact_text(title).strip()[:240],
        "detail": redact_text(detail).strip()[:500],
        "dedupe_key": redact_text(dedupe_key).strip()[:240],
        "task_id": (str(task_id).strip() if task_id else None),
        "ask_operator": 1 if ask_operator else 0,
        "status": "pending" if ask_operator else "recorded",
        "resolution": "",
        "resolved_at": None,
        "payload_json": json.dumps(redact_payload(payload or {})),
        "created_at": stamp,
    }
    with managed_connection() as connection:
        ensure_autonomy_receipt_schema(connection)
        placeholders = ", ".join("?" for _ in RECEIPT_COLUMNS)
        connection.execute(
            f"""
            INSERT INTO autonomy_attention_receipts ({", ".join(RECEIPT_COLUMNS)})
            VALUES ({placeholders})
            """,
            tuple(record[column] for column in RECEIPT_COLUMNS),
        )
        connection.commit()
    stored = {
        **{key: record[key] for key in RECEIPT_COLUMNS if key != "payload_json"},
        "ask_operator": bool(record["ask_operator"]),
        "payload": redact_payload(payload or {}),
    }
    return deepcopy(stored)


def get_receipt(receipt_id: str) -> dict[str, Any] | None:
    cleaned = str(receipt_id or "").strip()
    if not cleaned:
        return None
    with managed_connection() as connection:
        ensure_autonomy_receipt_schema(connection)
        row = connection.execute(
            "SELECT * FROM autonomy_attention_receipts WHERE receipt_id = ?",
            (cleaned,),
        ).fetchone()
    return row_to_record(row) if row is not None else None


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
    with managed_connection() as connection:
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
    return [row_to_record(row) for row in rows]


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
    with managed_connection() as connection:
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
    stamp = utc_now_iso()
    with managed_connection() as connection:
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
    with managed_connection() as connection:
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
