"""Completion gate for Lead-plan synthesis."""

from __future__ import annotations

from typing import Any, Callable

from app.workspace_agents import lead_plan_store

_BLOCKING_TASK_STATUSES = frozenset({"failed", "cancelled"})


def block_synthesis_if_needed(
    *,
    plan_id: str,
    workspace_id: str,
    tasks: list[dict[str, Any]],
    build_findings: Callable[
        [str, list[dict[str, Any]]],
        tuple[str, list[dict[str, Any]]],
    ],
) -> dict[str, Any] | None:
    blocked = [
        str(task["task_id"])
        for task in tasks
        if str(task.get("status") or "").strip().lower() in _BLOCKING_TASK_STATUSES
    ]
    prior = next(
        (
            row
            for row in lead_plan_store.list_receipts(plan_id)
            if str(row.get("kind") or "") == "lead_synthesis_blocked"
        ),
        None,
    )
    if not blocked and prior is None:
        return None
    summary, findings = build_findings(workspace_id, tasks)
    if prior is None:
        lead_plan_store.set_plan_status(plan_id, "awaiting_engagement")
        prior = lead_plan_store.append_receipt(
            plan_id=plan_id,
            workspace_id=workspace_id,
            kind="lead_synthesis_blocked",
            payload={
                "summary": summary,
                "findings": findings,
                "blocked_task_ids": blocked,
            },
        )
    return {
        "plan_id": plan_id,
        "status": "blocked",
        "summary": summary,
        "findings": findings,
        "blocked_task_ids": blocked,
        "receipt_id": prior.get("receipt_id"),
    }
