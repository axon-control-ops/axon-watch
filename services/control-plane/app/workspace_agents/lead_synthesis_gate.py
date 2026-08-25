"""Completion gate for Lead-plan synthesis."""

from __future__ import annotations

from typing import Any, Callable

from app.persistence import run_store
from app.workspace_agents import lead_plan_store
from app.workspace_agents.completion_gate import implementation_requested

_BLOCKING_TASK_STATUSES = frozenset({"failed", "cancelled"})


def _task_runs_by_task_id() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for run in run_store.list_runs():
        task_id = str(run.get("task_id") or "").strip()
        if task_id:
            grouped.setdefault(task_id, []).append(run)
    return grouped


def _latest_completion_gate(run: dict[str, Any]) -> dict[str, Any] | None:
    history_ref = str(run.get("history_ref") or "")
    if not history_ref:
        return None
    latest: dict[str, Any] | None = None
    for item in run_store.list_history(history_ref):
        receipt = item.get("receipt") if isinstance(item, dict) else None
        if not isinstance(receipt, dict):
            continue
        if str(receipt.get("type") or "") == "completion_gate":
            latest = receipt
    return latest


def _completion_gate_failure_reasons(tasks: list[dict[str, Any]]) -> list[str]:
    runs_by_task = _task_runs_by_task_id()
    reasons: list[str] = []
    for task in tasks:
        status = str(task.get("status") or "").strip().lower()
        if status != "completed" or not implementation_requested(task):
            continue
        task_id = str(task.get("task_id") or "").strip()
        runs = runs_by_task.get(task_id) or []
        if not runs:
            reasons.append(f"{task_id}: missing implementation run receipt")
            continue
        latest = _latest_completion_gate(runs[-1])
        summary = str((latest or {}).get("summary") or "")
        if not latest or "completion=pass" not in summary:
            reasons.append(f"{task_id}: missing passing completion gate receipt")
            continue
        if "commit=pending" in summary or "commit=" not in summary:
            reasons.append(f"{task_id}: missing delivery commit hash")
    return reasons


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
    gate_failures = _completion_gate_failure_reasons(tasks)
    prior = next(
        (
            row
            for row in lead_plan_store.list_receipts(plan_id)
            if str(row.get("kind") or "") == "lead_synthesis_blocked"
        ),
        None,
    )
    if not blocked and not gate_failures:
        if prior is not None:
            lead_plan_store.set_plan_status(plan_id, "active")
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
                "gate_failures": gate_failures,
            },
        )
    return {
        "plan_id": plan_id,
        "status": "blocked",
        "summary": summary,
        "findings": findings,
        "blocked_task_ids": blocked,
        "gate_failures": gate_failures,
        "receipt_id": prior.get("receipt_id"),
    }
