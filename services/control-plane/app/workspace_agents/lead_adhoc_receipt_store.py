"""Workspace-scoped ad-hoc Lead synthesis / VAXON handoff receipts.

Plan-linked handoffs live in lead_plan_store. Ad-hoc IDE specialist completions
use this ledger so REPORT can read Lead-verified rollups without parsing raw
specialist transcripts.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from typing import Any
from uuid import uuid4

from app.persistence import run_store_sqlite

KIND_LEAD_SYNTHESIS = "lead_adhoc_synthesis"
KIND_VAXON_POSTED = "lead_adhoc_vaxon_posted"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@contextmanager
def _connection():
    connection = run_store_sqlite.connect(os.environ.get("AXON_WATCH_CONTROL_PLANE_DB"))
    try:
        ensure_lead_adhoc_receipt_schema(connection)
        yield connection
    finally:
        connection.close()


def ensure_lead_adhoc_receipt_schema(connection: Any) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS lead_adhoc_receipts (
            receipt_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_lead_adhoc_receipts_workspace
            ON lead_adhoc_receipts(workspace_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_lead_adhoc_receipts_run_kind
            ON lead_adhoc_receipts(run_id, kind);
        """
    )
    connection.commit()


def _row_to_record(row: Any) -> dict[str, Any]:
    payload = json.loads(str(row["payload_json"] or "{}"))
    return {
        "receipt_id": row["receipt_id"],
        "workspace_id": row["workspace_id"],
        "run_id": row["run_id"],
        "kind": row["kind"],
        "payload": payload if isinstance(payload, dict) else {},
        "created_at": row["created_at"],
    }


def append_receipt(
    *,
    workspace_id: str,
    run_id: str,
    kind: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    receipt = {
        "receipt_id": f"lead-adhoc-{uuid4().hex[:16]}",
        "workspace_id": workspace_id.strip(),
        "run_id": run_id.strip(),
        "kind": kind.strip(),
        "payload": payload,
        "created_at": _now(),
    }
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO lead_adhoc_receipts (
                receipt_id, workspace_id, run_id, kind, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                receipt["receipt_id"],
                receipt["workspace_id"],
                receipt["run_id"],
                receipt["kind"],
                json.dumps(payload, sort_keys=True),
                receipt["created_at"],
            ),
        )
        connection.commit()
    return receipt


def find_receipt_for_run(*, run_id: str, kind: str) -> dict[str, Any] | None:
    cleaned_run = run_id.strip()
    cleaned_kind = kind.strip()
    if not cleaned_run or not cleaned_kind:
        return None
    with _connection() as connection:
        row = connection.execute(
            """
            SELECT * FROM lead_adhoc_receipts
            WHERE run_id = ? AND kind = ?
            ORDER BY created_at DESC, receipt_id DESC
            LIMIT 1
            """,
            (cleaned_run, cleaned_kind),
        ).fetchone()
    return _row_to_record(row) if row is not None else None


def list_receipts_for_workspace(
    workspace_id: str,
    *,
    kind: str | None = None,
    limit: int = 40,
) -> list[dict[str, Any]]:
    cleaned = workspace_id.strip()
    if not cleaned:
        return []
    max_limit = max(1, min(200, int(limit or 40)))
    with _connection() as connection:
        if kind:
            rows = connection.execute(
                """
                SELECT * FROM lead_adhoc_receipts
                WHERE workspace_id = ? AND kind = ?
                ORDER BY created_at DESC, receipt_id DESC
                LIMIT ?
                """,
                (cleaned, kind.strip(), max_limit),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT * FROM lead_adhoc_receipts
                WHERE workspace_id = ?
                ORDER BY created_at DESC, receipt_id DESC
                LIMIT ?
                """,
                (cleaned, max_limit),
            ).fetchall()
    return [_row_to_record(row) for row in rows]


def list_verified_vaxon_handoffs(
    *,
    workspace_id: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Lead-verified VAXON publications for deterministic REPORT."""
    max_limit = max(1, min(100, int(limit or 20)))
    with _connection() as connection:
        if workspace_id and workspace_id.strip():
            rows = connection.execute(
                """
                SELECT * FROM lead_adhoc_receipts
                WHERE kind = ? AND workspace_id = ?
                ORDER BY created_at DESC, receipt_id DESC
                LIMIT ?
                """,
                (KIND_VAXON_POSTED, workspace_id.strip(), max_limit),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT * FROM lead_adhoc_receipts
                WHERE kind = ?
                ORDER BY created_at DESC, receipt_id DESC
                LIMIT ?
                """,
                (KIND_VAXON_POSTED, max_limit),
            ).fetchall()
    return [_row_to_record(row) for row in rows]


def reset_store() -> None:
    with _connection() as connection:
        connection.execute("DELETE FROM lead_adhoc_receipts")
        connection.commit()


__all__ = [
    "KIND_LEAD_SYNTHESIS",
    "KIND_VAXON_POSTED",
    "append_receipt",
    "ensure_lead_adhoc_receipt_schema",
    "find_receipt_for_run",
    "list_receipts_for_workspace",
    "list_verified_vaxon_handoffs",
    "reset_store",
]
