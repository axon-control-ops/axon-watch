"""Durable Lead plans and replan/synthesis receipts (Gate 5)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from typing import Any
from uuid import uuid4

from app.persistence import run_store_sqlite


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@contextmanager
def _connection():
    connection = run_store_sqlite.connect(os.environ.get("AXON_WATCH_CONTROL_PLANE_DB"))
    try:
        ensure_lead_plan_schema(connection)
        yield connection
    finally:
        connection.close()


def ensure_lead_plan_schema(connection: Any) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS lead_plans (
            plan_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            goal TEXT NOT NULL,
            mode TEXT NOT NULL,
            status TEXT NOT NULL,
            plan_json TEXT NOT NULL,
            supersedes_plan_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_lead_plans_workspace_status
            ON lead_plans(workspace_id, status, updated_at DESC);
        CREATE TABLE IF NOT EXISTS lead_plan_tasks (
            plan_id TEXT NOT NULL,
            plan_key TEXT NOT NULL,
            task_id TEXT NOT NULL,
            PRIMARY KEY(plan_id, plan_key)
        );
        CREATE TABLE IF NOT EXISTS lead_plan_receipts (
            receipt_id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_lead_plan_receipts_plan
            ON lead_plan_receipts(plan_id, created_at ASC);
        """
    )
    connection.commit()


def _decode_plan(row: Any) -> dict[str, Any]:
    payload = json.loads(str(row["plan_json"] or "{}"))
    return {
        "plan_id": row["plan_id"],
        "workspace_id": row["workspace_id"],
        "goal": row["goal"],
        "mode": row["mode"],
        "status": row["status"],
        "plan": payload if isinstance(payload, dict) else {},
        "supersedes_plan_id": row["supersedes_plan_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def persist_plan(
    *,
    workspace_id: str,
    plan: dict[str, Any],
    plan_key_to_task_id: dict[str, str],
    supersedes_plan_id: str | None = None,
) -> dict[str, Any]:
    timestamp = _now()
    plan_id = f"lead-plan-{uuid4().hex[:16]}"
    goal = str(plan.get("goal") or "").strip()
    mode = str(plan.get("mode") or "sequential").strip()
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO lead_plans (
                plan_id, workspace_id, goal, mode, status, plan_json,
                supersedes_plan_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?)
            """,
            (
                plan_id,
                workspace_id,
                goal,
                mode,
                json.dumps(plan, sort_keys=True),
                supersedes_plan_id,
                timestamp,
                timestamp,
            ),
        )
        connection.executemany(
            "INSERT INTO lead_plan_tasks (plan_id, plan_key, task_id) VALUES (?, ?, ?)",
            [
                (plan_id, plan_key, task_id)
                for plan_key, task_id in plan_key_to_task_id.items()
            ],
        )
        connection.commit()
    append_receipt(
        plan_id=plan_id,
        workspace_id=workspace_id,
        kind="lead_plan_persisted",
        payload={
            "goal": goal,
            "mode": mode,
            "task_count": len(plan_key_to_task_id),
            "supersedes_plan_id": supersedes_plan_id,
        },
    )
    stored = get_plan(plan_id)
    assert stored is not None
    return stored


def get_plan(plan_id: str) -> dict[str, Any] | None:
    with _connection() as connection:
        row = connection.execute(
            "SELECT * FROM lead_plans WHERE plan_id = ?",
            (plan_id.strip(),),
        ).fetchone()
    return _decode_plan(row) if row else None


def latest_active_plan(workspace_id: str) -> dict[str, Any] | None:
    with _connection() as connection:
        row = connection.execute(
            """
            SELECT * FROM lead_plans
            WHERE workspace_id = ? AND status = 'active'
            ORDER BY updated_at DESC, rowid DESC
            LIMIT 1
            """,
            (workspace_id.strip(),),
        ).fetchone()
    return _decode_plan(row) if row else None


def plan_task_links(plan_id: str) -> list[dict[str, str]]:
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT plan_key, task_id
            FROM lead_plan_tasks
            WHERE plan_id = ?
            ORDER BY plan_key ASC
            """,
            (plan_id.strip(),),
        ).fetchall()
    return [{"plan_key": row["plan_key"], "task_id": row["task_id"]} for row in rows]


def set_plan_status(plan_id: str, status: str) -> dict[str, Any]:
    cleaned = status.strip().lower()
    if cleaned not in {"active", "superseded", "completed", "cancelled"}:
        raise ValueError(f"invalid lead plan status: {status}")
    with _connection() as connection:
        connection.execute(
            "UPDATE lead_plans SET status = ?, updated_at = ? WHERE plan_id = ?",
            (cleaned, _now(), plan_id.strip()),
        )
        if connection.total_changes != 1:
            raise ValueError(f"lead plan not found: {plan_id}")
        connection.commit()
    stored = get_plan(plan_id)
    assert stored is not None
    return stored


def append_receipt(
    *,
    plan_id: str,
    workspace_id: str,
    kind: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    receipt = {
        "receipt_id": f"lead-receipt-{uuid4().hex[:16]}",
        "plan_id": plan_id.strip(),
        "workspace_id": workspace_id.strip(),
        "kind": kind.strip(),
        "payload": payload,
        "created_at": _now(),
    }
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO lead_plan_receipts (
                receipt_id, plan_id, workspace_id, kind, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                receipt["receipt_id"],
                receipt["plan_id"],
                receipt["workspace_id"],
                receipt["kind"],
                json.dumps(payload, sort_keys=True),
                receipt["created_at"],
            ),
        )
        connection.commit()
    return receipt


def list_receipts(plan_id: str) -> list[dict[str, Any]]:
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM lead_plan_receipts
            WHERE plan_id = ?
            ORDER BY created_at ASC, receipt_id ASC
            """,
            (plan_id.strip(),),
        ).fetchall()
    return [
        {
            "receipt_id": row["receipt_id"],
            "plan_id": row["plan_id"],
            "workspace_id": row["workspace_id"],
            "kind": row["kind"],
            "payload": json.loads(str(row["payload_json"] or "{}")),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def reset_store() -> None:
    with _connection() as connection:
        connection.execute("DELETE FROM lead_plan_receipts")
        connection.execute("DELETE FROM lead_plan_tasks")
        connection.execute("DELETE FROM lead_plans")
        connection.commit()


__all__ = [
    "append_receipt",
    "get_plan",
    "latest_active_plan",
    "list_receipts",
    "persist_plan",
    "plan_task_links",
    "reset_store",
    "set_plan_status",
]
