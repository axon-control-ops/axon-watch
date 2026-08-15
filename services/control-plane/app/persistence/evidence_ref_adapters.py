"""Adapters that index existing control-plane receipts into evidence_registry."""

from __future__ import annotations

import json
import os
from typing import Any

from app.persistence import run_store_sqlite
from app.persistence.constitution_registry_store import ensure_schema, index_evidence


def _connection():
    connection = run_store_sqlite.connect(os.environ.get("AXON_WATCH_CONTROL_PLANE_DB"))
    ensure_schema(connection)
    return connection


def index_run_history_transition(
    *,
    history_ref: str,
    sequence: int,
    transition: dict[str, Any],
    workspace_id: str = "",
    run_id: str | None = None,
    task_id: str | None = None,
    mission_id: str | None = None,
) -> dict[str, Any]:
    source_id = f"{history_ref}:{int(sequence)}"
    receipt = transition.get("receipt") if isinstance(transition.get("receipt"), dict) else {}
    kind = str(receipt.get("type") or transition.get("phase") or "run_transition")
    summary = (
        str(receipt.get("summary") or "").strip()
        or str(transition.get("summary") or "").strip()
        or str(transition.get("current_step") or "").strip()
        or f"Run history transition {source_id}"
    )
    return index_evidence(
        source_table="run_history",
        source_id=source_id,
        source_ref={
            "history_ref": history_ref,
            "sequence": int(sequence),
        },
        kind=kind,
        summary=summary,
        workspace_id=workspace_id,
        run_id=run_id,
        task_id=task_id,
        mission_id=mission_id,
        tags=["run_history", kind],
    )


def backfill_run_history(*, limit: int = 200) -> int:
    """Index recent run_history transitions.

    The actual run_history schema is `(history_ref, sequence, transition_json)`;
    run/workspace/task metadata is resolved through the `runs` table when
    available.
    """
    capped = max(1, min(int(limit or 200), 500))
    count = 0
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT
                rh.history_ref,
                rh.sequence,
                rh.transition_json,
                r.run_id,
                r.workspace_id,
                r.task_id
            FROM run_history rh
            LEFT JOIN runs r ON r.history_ref = rh.history_ref
            WHERE NOT EXISTS (
                SELECT 1
                FROM evidence_registry e
                WHERE e.source_table = 'run_history'
                  AND e.source_id = rh.history_ref || ':' || rh.sequence
            )
            ORDER BY rh.history_ref DESC, rh.sequence DESC
            LIMIT ?
            """,
            (capped,),
        ).fetchall()
    for row in rows:
        try:
            transition = json.loads(str(row["transition_json"] or "{}"))
        except json.JSONDecodeError:
            transition = {}
        if not isinstance(transition, dict):
            transition = {}
        index_run_history_transition(
            history_ref=str(row["history_ref"]),
            sequence=int(row["sequence"]),
            transition=transition,
            workspace_id=str(row["workspace_id"] or ""),
            run_id=row["run_id"],
            task_id=row["task_id"],
        )
        count += 1
    return count


def index_lead_plan_receipt(
    *,
    receipt_id: str,
    plan_id: str,
    workspace_id: str = "",
    kind: str = "",
    summary: str = "",
    mission_id: str | None = None,
) -> dict[str, Any]:
    return index_evidence(
        source_table="lead_plan_receipts",
        source_id=receipt_id,
        source_ref={"receipt_id": receipt_id, "plan_id": plan_id},
        kind=kind or "lead_plan_receipt",
        summary=summary or f"Lead plan receipt {receipt_id}",
        workspace_id=workspace_id,
        mission_id=mission_id,
        tags=["lead_plan", kind] if kind else ["lead_plan"],
    )


def backfill_lead_plan_receipts(*, limit: int = 200) -> int:
    capped = max(1, min(int(limit or 200), 500))
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT receipt_id, plan_id, workspace_id, kind, payload_json
            FROM lead_plan_receipts r
            WHERE NOT EXISTS (
                SELECT 1
                FROM evidence_registry e
                WHERE e.source_table = 'lead_plan_receipts'
                  AND e.source_id = r.receipt_id
            )
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (capped,),
        ).fetchall()
    count = 0
    for row in rows:
        payload_summary = ""
        try:
            payload = json.loads(str(row["payload_json"] or "{}"))
            if isinstance(payload, dict):
                payload_summary = str(payload.get("summary") or payload.get("goal") or "").strip()
        except json.JSONDecodeError:
            payload_summary = ""
        index_lead_plan_receipt(
            receipt_id=str(row["receipt_id"]),
            plan_id=str(row["plan_id"]),
            workspace_id=str(row["workspace_id"] or ""),
            kind=str(row["kind"] or ""),
            summary=payload_summary,
        )
        count += 1
    return count


def index_autonomy_receipt(
    *,
    receipt_id: str,
    workspace_id: str = "",
    decision: str = "",
    tier: str = "",
    risk: str = "",
    task_id: str | None = None,
    summary: str = "",
    mission_id: str | None = None,
    decision_id: str | None = None,
) -> dict[str, Any]:
    return index_evidence(
        source_table="autonomy_attention_receipts",
        source_id=receipt_id,
        source_ref={"receipt_id": receipt_id},
        kind="autonomy_attention",
        summary=summary or f"Autonomy decision {decision or receipt_id}",
        workspace_id=workspace_id,
        task_id=task_id,
        mission_id=mission_id,
        decision_id=decision_id,
        tags=["autonomy", decision, tier, risk],
    )


def backfill_autonomy_receipts(*, limit: int = 200) -> int:
    capped = max(1, min(int(limit or 200), 500))
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT receipt_id, workspace_id, decision, tier, risk, title, detail, task_id
            FROM autonomy_attention_receipts r
            WHERE NOT EXISTS (
                SELECT 1
                FROM evidence_registry e
                WHERE e.source_table = 'autonomy_attention_receipts'
                  AND e.source_id = r.receipt_id
            )
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (capped,),
        ).fetchall()
    count = 0
    for row in rows:
        summary = str(row["title"] or row["detail"] or "").strip()
        index_autonomy_receipt(
            receipt_id=str(row["receipt_id"]),
            workspace_id=str(row["workspace_id"] or ""),
            decision=str(row["decision"] or ""),
            tier=str(row["tier"] or ""),
            risk=str(row["risk"] or ""),
            task_id=row["task_id"],
            summary=summary,
        )
        count += 1
    return count


def index_host_action_receipt(
    *,
    receipt_id: str,
    device_id: str = "",
    command_id: str = "",
    status: str = "",
    summary: str = "",
    mission_id: str | None = None,
    decision_id: str | None = None,
) -> dict[str, Any]:
    return index_evidence(
        source_table="host_action_receipts",
        source_id=receipt_id,
        source_ref={"receipt_id": receipt_id, "device_id": device_id, "command_id": command_id},
        kind="host_action",
        summary=summary or f"Host action receipt {receipt_id}",
        mission_id=mission_id,
        decision_id=decision_id,
        tags=["host_action", status],
    )


def backfill_host_action_receipts(*, limit: int = 200) -> int:
    capped = max(1, min(int(limit or 200), 500))
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT receipt_id, device_id, command_id, status, result_summary
            FROM host_action_receipts r
            WHERE NOT EXISTS (
                SELECT 1
                FROM evidence_registry e
                WHERE e.source_table = 'host_action_receipts'
                  AND e.source_id = r.receipt_id
            )
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (capped,),
        ).fetchall()
    count = 0
    for row in rows:
        index_host_action_receipt(
            receipt_id=str(row["receipt_id"]),
            device_id=str(row["device_id"] or ""),
            command_id=str(row["command_id"] or ""),
            status=str(row["status"] or ""),
            summary=str(row["result_summary"] or ""),
        )
        count += 1
    return count


def index_workspace_delivery(
    *,
    delivery_id: str,
    workspace_id: str = "",
    run_id: str | None = None,
    task_id: str | None = None,
    stage: str = "",
    summary: str = "",
    mission_id: str | None = None,
) -> dict[str, Any]:
    return index_evidence(
        source_table="workspace_deliveries",
        source_id=delivery_id,
        source_ref={"delivery_id": delivery_id},
        kind="workspace_delivery",
        summary=summary or f"Workspace delivery {delivery_id} reached {stage or 'unknown'}",
        workspace_id=workspace_id,
        run_id=run_id,
        task_id=task_id,
        mission_id=mission_id,
        tags=["delivery", stage],
    )


def backfill_workspace_deliveries(*, limit: int = 200) -> int:
    capped = max(1, min(int(limit or 200), 500))
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT delivery_id, workspace_id, run_id, task_id, stage, blocker
            FROM workspace_deliveries r
            WHERE NOT EXISTS (
                SELECT 1
                FROM evidence_registry e
                WHERE e.source_table = 'workspace_deliveries'
                  AND e.source_id = r.delivery_id
            )
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (capped,),
        ).fetchall()
    count = 0
    for row in rows:
        index_workspace_delivery(
            delivery_id=str(row["delivery_id"]),
            workspace_id=str(row["workspace_id"] or ""),
            run_id=row["run_id"],
            task_id=row["task_id"],
            stage=str(row["stage"] or ""),
            summary=str(row["blocker"] or ""),
        )
        count += 1
    return count


def backfill_all(*, limit_per_source: int = 200) -> dict[str, int]:
    """Backfill known source tables into evidence_registry.

    Missing optional source tables are skipped because different deployments
    may not have emitted every receipt type yet.
    """
    results: dict[str, int] = {}
    for name, fn in (
        ("run_history", backfill_run_history),
        ("lead_plan_receipts", backfill_lead_plan_receipts),
        ("autonomy_attention_receipts", backfill_autonomy_receipts),
        ("host_action_receipts", backfill_host_action_receipts),
        ("workspace_deliveries", backfill_workspace_deliveries),
    ):
        try:
            results[name] = fn(limit=limit_per_source)
        except Exception as exc:  # noqa: BLE001 - backfill should be best-effort per source
            results[name] = 0
            results[f"{name}_error"] = str(exc)
    return results
