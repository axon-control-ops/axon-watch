"""Receipt-backed Lead replans and deterministic specialist synthesis (Gate 5)."""

from __future__ import annotations

from typing import Any

from app.persistence import task_store
from app.runs.service import RunLifecycleError, RunNotFoundError, stop_run
from app.workspace_agents import lead_plan_store
from app.workspace_agents.lead_fan_out import materialize_lead_fan_out
from app.workspace_agents.lead_task_plan import PlanMode

_TERMINAL_TASK_STATUSES = frozenset({"completed", "failed", "cancelled"})


class LeadReplanError(ValueError):
    """Raised when an explicit replan or synthesis cannot be completed."""


def _plan_tasks(plan_id: str) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for link in lead_plan_store.plan_task_links(plan_id):
        task = task_store.get_task(link["task_id"])
        if task is not None:
            tasks.append({**task, "plan_key": link["plan_key"]})
    return tasks


def _cancel_obsolete_tasks(plan_id: str) -> tuple[list[str], list[dict[str, str]]]:
    cancelled: list[str] = []
    stop_errors: list[dict[str, str]] = []
    active_tasks = [
        task
        for task in _plan_tasks(plan_id)
        if str(task.get("status") or "").strip().lower()
        not in _TERMINAL_TASK_STATUSES
    ]
    # Stop every leased run first. Fail closed: never release path ownership and
    # start replacement work while an old process might still be running.
    for task in active_tasks:
        status = str(task.get("status") or "").strip().lower()
        run_id = str(task.get("run_id") or "").strip()
        if status == "leased" and run_id:
            try:
                stop_run(run_id)
            except (RunLifecycleError, RunNotFoundError, OSError, RuntimeError) as exc:
                stop_errors.append({"run_id": run_id, "detail": str(exc)})
    if stop_errors:
        return cancelled, stop_errors
    for task in active_tasks:
        task_store.cancel_task(
            str(task["task_id"]),
            terminal_outcome=f"superseded by Lead replan from {plan_id}",
        )
        cancelled.append(str(task["task_id"]))
    return cancelled, stop_errors


def replan_lead_goal(
    *,
    workspace_id: str,
    goal: str,
    mode: PlanMode = "auto",
    create_runs: bool = True,
) -> dict[str, Any]:
    """Supersede the active plan, cancel obsolete work, and materialize a new plan."""
    workspace = workspace_id.strip()
    cleaned_goal = " ".join((goal or "").strip().split())
    if not workspace:
        raise LeadReplanError("workspace_id is required")
    if not cleaned_goal:
        raise LeadReplanError("goal is required")

    previous = lead_plan_store.latest_active_plan(workspace)
    previous_plan_id = str(previous["plan_id"]) if previous else None
    cancelled: list[str] = []
    stop_errors: list[dict[str, str]] = []
    if previous_plan_id:
        cancelled, stop_errors = _cancel_obsolete_tasks(previous_plan_id)
        if stop_errors:
            lead_plan_store.append_receipt(
                plan_id=previous_plan_id,
                workspace_id=workspace,
                kind="lead_replan_blocked",
                payload={
                    "replacement_goal": cleaned_goal,
                    "stop_errors": stop_errors,
                },
            )
            raise LeadReplanError(
                "replan blocked because obsolete worker runs could not be stopped"
            )
        lead_plan_store.set_plan_status(previous_plan_id, "superseded")
        lead_plan_store.append_receipt(
            plan_id=previous_plan_id,
            workspace_id=workspace,
            kind="lead_plan_superseded",
            payload={
                "replacement_goal": cleaned_goal,
                "cancelled_task_ids": cancelled,
                "stop_errors": stop_errors,
            },
        )

    materialized = materialize_lead_fan_out(
        workspace_id=workspace,
        goal=cleaned_goal,
        mode=mode,
        create_runs=create_runs,
        supersedes_plan_id=previous_plan_id,
    )
    receipt = lead_plan_store.append_receipt(
        plan_id=str(materialized["plan_id"]),
        workspace_id=workspace,
        kind="lead_replan_materialized",
        payload={
            "supersedes_plan_id": previous_plan_id,
            "cancelled_task_ids": cancelled,
            "stop_errors": stop_errors,
        },
    )
    return {
        **materialized,
        "replan": {
            "supersedes_plan_id": previous_plan_id,
            "cancelled_task_ids": cancelled,
            "stop_errors": stop_errors,
            "receipt_id": receipt["receipt_id"],
        },
    }


def synthesize_lead_plan(plan_id: str) -> dict[str, Any]:
    """Summarize terminal specialist task outcomes and persist a synthesis receipt."""
    plan = lead_plan_store.get_plan(plan_id)
    if plan is None:
        raise LeadReplanError(f"lead plan not found: {plan_id}")
    tasks = _plan_tasks(plan_id)
    pending = [
        str(task["task_id"])
        for task in tasks
        if str(task.get("status") or "").strip().lower() not in _TERMINAL_TASK_STATUSES
    ]
    if pending:
        return {
            "plan_id": plan_id,
            "status": "awaiting_results",
            "pending_task_ids": pending,
            "summary": "",
        }

    findings = [
        {
            "task_id": str(task["task_id"]),
            "plan_key": str(task.get("plan_key") or ""),
            "owner_role": str(task.get("owner_role") or ""),
            "status": str(task.get("status") or ""),
            "outcome": str(task.get("terminal_outcome") or ""),
        }
        for task in tasks
    ]
    summary = "; ".join(
        f"{row['owner_role']}={row['status']}"
        + (f" ({row['outcome']})" if row["outcome"] else "")
        for row in findings
    )
    lead_plan_store.set_plan_status(plan_id, "completed")
    receipt = lead_plan_store.append_receipt(
        plan_id=plan_id,
        workspace_id=str(plan["workspace_id"]),
        kind="lead_synthesis_completed",
        payload={"summary": summary, "findings": findings},
    )
    return {
        "plan_id": plan_id,
        "status": "completed",
        "summary": summary,
        "findings": findings,
        "receipt_id": receipt["receipt_id"],
    }


__all__ = [
    "LeadReplanError",
    "replan_lead_goal",
    "synthesize_lead_plan",
]
