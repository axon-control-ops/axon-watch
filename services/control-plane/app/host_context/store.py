"""SQLite persistence for host snapshots, events, artifacts, receipts, policy."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import os
from typing import Any

from app.host_context.models import utc_now_iso
from app.persistence import run_store_sqlite

_POLICY_KEY = "default"


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


def default_policy() -> dict[str, Any]:
    return {
        "awareness_paused": False,
        "deny_overrides_enabled": False,
        "retention_days": 14,
        "max_artifacts": 500,
        "max_events": 1000,
        "allowlisted_roots": ["Documents", "Downloads", "Pictures", "Videos"],
        "updated_at": "",
    }


def load_policy() -> dict[str, Any]:
    with _managed_connection() as connection:
        row = connection.execute(
            """
            SELECT policy_json FROM host_policy WHERE policy_key = ?
            """,
            (_POLICY_KEY,),
        ).fetchone()
    if not row:
        return default_policy()
    raw = json.loads(row["policy_json"] or "{}")
    merged = default_policy()
    if isinstance(raw, dict):
        merged.update(raw)
    return merged


def save_policy(policy: dict[str, Any]) -> dict[str, Any]:
    merged = default_policy()
    merged.update(policy)
    from app.host_context.models import utc_now_iso

    merged["updated_at"] = utc_now_iso()
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO host_policy (policy_key, policy_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(policy_key) DO UPDATE SET
                policy_json = excluded.policy_json,
                updated_at = excluded.updated_at
            """,
            (_POLICY_KEY, json.dumps(merged, separators=(",", ":"), sort_keys=True), merged["updated_at"]),
        )
        connection.commit()
    return merged


def upsert_snapshot(record: dict[str, Any]) -> dict[str, Any]:
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO host_snapshots (
                snapshot_id, device_id, generated_at, payload_json
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(snapshot_id) DO UPDATE SET
                device_id = excluded.device_id,
                generated_at = excluded.generated_at,
                payload_json = excluded.payload_json
            """,
            (
                record["snapshot_id"],
                record["device_id"],
                record["generated_at"],
                json.dumps(record, separators=(",", ":"), sort_keys=True),
            ),
        )
        connection.execute(
            """
            INSERT INTO host_devices (
                device_id, hostname, platform, last_seen_at, capabilities_json, status
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                hostname = excluded.hostname,
                platform = excluded.platform,
                last_seen_at = excluded.last_seen_at,
                capabilities_json = excluded.capabilities_json,
                status = excluded.status
            """,
            (
                record["device_id"],
                str((record.get("host") or {}).get("hostname") or ""),
                str((record.get("host") or {}).get("platform") or ""),
                record["generated_at"],
                json.dumps(record.get("capabilities") or [], separators=(",", ":")),
                "online",
            ),
        )
        connection.commit()
    return record


def latest_snapshot(device_id: str | None = None) -> dict[str, Any] | None:
    clauses: list[str] = []
    values: list[Any] = []
    if device_id:
        clauses.append("device_id = ?")
        values.append(device_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with _managed_connection() as connection:
        row = connection.execute(
            f"""
            SELECT payload_json FROM host_snapshots
            {where}
            ORDER BY generated_at DESC, rowid DESC
            LIMIT 1
            """,
            tuple(values),
        ).fetchone()
    if not row:
        return None
    payload = json.loads(row["payload_json"] or "{}")
    return payload if isinstance(payload, dict) else None


def insert_event(record: dict[str, Any]) -> dict[str, Any]:
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO host_events (
                event_id, device_id, kind, title, detail, occurred_at,
                artifact_id, sensitivity, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["event_id"],
                record["device_id"],
                record["kind"],
                record["title"],
                record["detail"],
                record["occurred_at"],
                record.get("artifact_id") or "",
                record.get("sensitivity") or "normal",
                json.dumps(record.get("meta") or {}, separators=(",", ":"), sort_keys=True),
            ),
        )
        connection.commit()
    return record


def list_events(*, device_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    clauses: list[str] = []
    values: list[Any] = []
    if device_id:
        clauses.append("device_id = ?")
        values.append(device_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    max_limit = max(1, min(200, int(limit or 50)))
    with _managed_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT * FROM host_events
            {where}
            ORDER BY occurred_at DESC, rowid DESC
            LIMIT ?
            """,
            (*values, max_limit),
        ).fetchall()
    return [_event_row(row) for row in rows]


def upsert_artifact(record: dict[str, Any]) -> dict[str, Any]:
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO host_artifacts (
                artifact_id, device_id, path, title, kind, mime_type, origin,
                sensitivity, modified_at, size_bytes, thumbnail_local,
                workspace_id, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(artifact_id) DO UPDATE SET
                path = excluded.path,
                title = excluded.title,
                kind = excluded.kind,
                mime_type = excluded.mime_type,
                origin = excluded.origin,
                sensitivity = excluded.sensitivity,
                modified_at = excluded.modified_at,
                size_bytes = excluded.size_bytes,
                thumbnail_local = excluded.thumbnail_local,
                workspace_id = excluded.workspace_id,
                meta_json = excluded.meta_json
            """,
            (
                record["artifact_id"],
                record["device_id"],
                record["path"],
                record["title"],
                record["kind"],
                record["mime_type"],
                record["origin"],
                record["sensitivity"],
                record["modified_at"],
                int(record.get("size_bytes") or 0),
                1 if record.get("thumbnail_local") else 0,
                record.get("workspace_id") or "",
                json.dumps(record.get("meta") or {}, separators=(",", ":"), sort_keys=True),
            ),
        )
        connection.commit()
    return record


def list_artifacts(
    *,
    device_id: str | None = None,
    query: str = "",
    limit: int = 40,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    values: list[Any] = []
    if device_id:
        clauses.append("device_id = ?")
        values.append(device_id)
    trimmed = query.strip().lower()
    if trimmed:
        like = f"%{trimmed}%"
        clauses.append("(lower(title) LIKE ? OR lower(path) LIKE ? OR lower(kind) LIKE ?)")
        values.extend([like, like, like])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    max_limit = max(1, min(200, int(limit or 40)))
    with _managed_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT * FROM host_artifacts
            {where}
            ORDER BY modified_at DESC, rowid DESC
            LIMIT ?
            """,
            (*values, max_limit),
        ).fetchall()
    return [_artifact_row(row) for row in rows]


def insert_receipt(record: dict[str, Any]) -> dict[str, Any]:
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO host_action_receipts (
                receipt_id, device_id, command_id, action, tier, status,
                result_summary, created_at, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["receipt_id"],
                record["device_id"],
                record.get("command_id") or "",
                record["action"],
                record.get("tier") or "auto",
                record.get("status") or "ok",
                record.get("result_summary") or "",
                record["created_at"],
                json.dumps(record.get("meta") or {}, separators=(",", ":"), sort_keys=True),
            ),
        )
        connection.commit()
    return record


def list_receipts(*, device_id: str | None = None, limit: int = 40) -> list[dict[str, Any]]:
    clauses: list[str] = []
    values: list[Any] = []
    if device_id:
        clauses.append("device_id = ?")
        values.append(device_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    max_limit = max(1, min(200, int(limit or 40)))
    with _managed_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT * FROM host_action_receipts
            {where}
            ORDER BY created_at DESC, rowid DESC
            LIMIT ?
            """,
            (*values, max_limit),
        ).fetchall()
    return [_receipt_row(row) for row in rows]


def list_devices(*, limit: int = 20) -> list[dict[str, Any]]:
    max_limit = max(1, min(50, int(limit or 20)))
    with _managed_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM host_devices
            ORDER BY last_seen_at DESC, rowid DESC
            LIMIT ?
            """,
            (max_limit,),
        ).fetchall()
    return [
        {
            "device_id": row["device_id"],
            "hostname": row["hostname"],
            "platform": row["platform"],
            "last_seen_at": row["last_seen_at"],
            "capabilities": json.loads(row["capabilities_json"] or "[]"),
            "status": row["status"],
        }
        for row in rows
    ]


def command_seen(command_id: str) -> bool:
    trimmed = str(command_id or "").strip()
    if not trimmed:
        return False
    with _managed_connection() as connection:
        row = connection.execute(
            """
            SELECT 1 FROM host_action_receipts WHERE command_id = ? LIMIT 1
            """,
            (trimmed,),
        ).fetchone()
    return row is not None


def prune_expired(*, retention_days: int | None = None) -> dict[str, int]:
    """Delete host rows older than retention_days (metadata only; no content logs)."""
    policy = load_policy()
    days = int(retention_days if retention_days is not None else policy.get("retention_days") or 14)
    days = max(1, min(365, days))
    cutoff = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=days)
    cutoff_iso = cutoff.isoformat().replace("+00:00", "Z")
    with _managed_connection() as connection:
        events = connection.execute(
            "DELETE FROM host_events WHERE occurred_at < ?",
            (cutoff_iso,),
        ).rowcount
        artifacts = connection.execute(
            "DELETE FROM host_artifacts WHERE modified_at < ?",
            (cutoff_iso,),
        ).rowcount
        snapshots = connection.execute(
            "DELETE FROM host_snapshots WHERE generated_at < ?",
            (cutoff_iso,),
        ).rowcount
        receipts = connection.execute(
            "DELETE FROM host_action_receipts WHERE created_at < ?",
            (cutoff_iso,),
        ).rowcount
        connection.commit()
    return {
        "retention_days": days,
        "events_deleted": int(events or 0),
        "artifacts_deleted": int(artifacts or 0),
        "snapshots_deleted": int(snapshots or 0),
        "receipts_deleted": int(receipts or 0),
        "pruned_before": cutoff_iso,
        "pruned_at": utc_now_iso(),
    }


def _event_row(row: Any) -> dict[str, Any]:
    return {
        "event_id": row["event_id"],
        "device_id": row["device_id"],
        "kind": row["kind"],
        "title": row["title"],
        "detail": row["detail"],
        "occurred_at": row["occurred_at"],
        "artifact_id": row["artifact_id"],
        "sensitivity": row["sensitivity"],
        "meta": json.loads(row["meta_json"] or "{}"),
    }


def _artifact_row(row: Any) -> dict[str, Any]:
    return {
        "artifact_id": row["artifact_id"],
        "device_id": row["device_id"],
        "path": row["path"],
        "title": row["title"],
        "kind": row["kind"],
        "mime_type": row["mime_type"],
        "origin": row["origin"],
        "sensitivity": row["sensitivity"],
        "modified_at": row["modified_at"],
        "size_bytes": int(row["size_bytes"] or 0),
        "thumbnail_local": bool(row["thumbnail_local"]),
        "workspace_id": row["workspace_id"],
        "meta": json.loads(row["meta_json"] or "{}"),
    }


def _receipt_row(row: Any) -> dict[str, Any]:
    return {
        "receipt_id": row["receipt_id"],
        "device_id": row["device_id"],
        "command_id": row["command_id"],
        "action": row["action"],
        "tier": row["tier"],
        "status": row["status"],
        "result_summary": row["result_summary"],
        "created_at": row["created_at"],
        "meta": json.loads(row["meta_json"] or "{}"),
    }
