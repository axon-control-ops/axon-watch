"""Lead fan-out — plan → ledger tasks → ready specialist runs (Gate 5)."""

from __future__ import annotations

from typing import Any

from app.persistence import task_store
from app.runs.service import append_run_execution_receipt, create_run
from app.workspace_agents import build_company_roster
from app.workspace_agents import lead_plan_store
from app.workspace_agents.lead_task_persist import persist_lead_task_plan
from app.workspace_agents.lead_task_plan import (
    LeadPlanRosterMember,
    PlanMode,
    build_lead_task_plan,
    detect_fan_out_intent,
)


class LeadFanOutError(ValueError):
    """Operator-facing fan-out / plan materialize failure."""


def _roster_from_company(workspace_id: str) -> list[LeadPlanRosterMember]:
    company = build_company_roster(workspace_id)
    rows = company.get("employees") if isinstance(company, dict) else None
    if not isinstance(rows, list):
        return []
    members: list[LeadPlanRosterMember] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        role = str(row.get("role") or "").strip().lower()
        if not role:
            continue
        members.append(
            LeadPlanRosterMember(
                role=role,
                name=str(row.get("name") or "").strip(),
                owns=str(row.get("owns") or "").strip(),
            )
        )
    return members


def _deps_completed(task: dict[str, Any]) -> bool:
    deps = task.get("dependencies")
    if not isinstance(deps, list) or not deps:
        return True
    for dep_id in deps:
        dep = task_store.get_task(str(dep_id))
        if dep is None:
            return False
        if str(dep.get("status") or "").strip().lower() != "completed":
            return False
    return True


def materialize_lead_fan_out(
    *,
    workspace_id: str,
    goal: str,
    mode: PlanMode = "auto",
    create_runs: bool = True,
    supersedes_plan_id: str | None = None,
) -> dict[str, Any]:
    """Build plan, persist tasks, and open leased runs for dependency-ready items.

    Does **not** start Lane B dispatch or enable the continuous scheduler.
    Ready runs appear on the task board / run list for operators and workers.
    """
    workspace = workspace_id.strip()
    cleaned_goal = " ".join((goal or "").strip().split())
    if not workspace:
        raise LeadFanOutError("workspace_id is required")
    if not cleaned_goal:
        raise LeadFanOutError("goal is required")

    roster = _roster_from_company(workspace)
    if not roster:
        raise LeadFanOutError(f"no company roster for workspace {workspace}")

    try:
        plan = build_lead_task_plan(goal=cleaned_goal, roster=roster, mode=mode)
    except ValueError as exc:
        raise LeadFanOutError(str(exc)) from exc

    persisted = persist_lead_task_plan(
        workspace_id=workspace,
        plan=plan,
        supersedes_plan_id=supersedes_plan_id,
    )
    plan_id = str(persisted["plan_id"])
    tasks_by_id = {str(row["task_id"]): row for row in persisted["tasks"]}
    runs: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []

    if create_runs:
        for row in persisted["tasks"]:
            task_id = str(row["task_id"])
            fresh = task_store.get_task(task_id) or row
            if not _deps_completed(fresh):
                deferred.append(
                    {
                        "task_id": task_id,
                        "plan_key": row.get("plan_key"),
                        "owner_role": fresh.get("owner_role"),
                        "reason": "dependencies_incomplete",
                    }
                )
                continue
            owner_role = str(fresh.get("owner_role") or "").strip().lower()
            holder = f"lead-fan-out-{workspace}-{owner_role}"
            try:
                leased = task_store.lease_task(task_id, lease_holder=holder)
            except task_store.TaskLedgerError as exc:
                deferred.append(
                    {
                        "task_id": task_id,
                        "plan_key": row.get("plan_key"),
                        "owner_role": owner_role,
                        "reason": str(exc),
                    }
                )
                continue
            summary = f"{owner_role}: {str(leased.get('goal') or cleaned_goal)[:120]}"
            run = create_run(
                workspace_id=workspace,
                mode="agent",
                summary=summary,
                detail=(
                    f"Lead fan-out ({plan.mode}) plan_key="
                    f"{row.get('plan_key')} task={task_id}"
                ),
                employee_role=owner_role,
                task_id=task_id,
                require_leased_task=True,
            )
            append_run_execution_receipt(
                str(run["run_id"]),
                receipt_type="lead_fan_out_assigned",
                receipt_summary=(
                    f"Lead assigned {owner_role} task {task_id} "
                    f"({row.get('plan_key')})"
                ),
                actor="lead_planner",
            )
            runs.append(
                {
                    "run_id": run["run_id"],
                    "task_id": task_id,
                    "plan_key": row.get("plan_key"),
                    "owner_role": owner_role,
                    "phase": run.get("phase"),
                }
            )
            tasks_by_id[task_id] = task_store.get_task(task_id) or leased

    receipt = lead_plan_store.append_receipt(
        plan_id=plan_id,
        workspace_id=workspace,
        kind="lead_fan_out_materialized",
        payload={
            "mode": plan.mode,
            "task_count": len(persisted["tasks"]),
            "run_ids": [str(run["run_id"]) for run in runs],
            "deferred_task_ids": [str(row["task_id"]) for row in deferred],
        },
    )
    return {
        "plan_id": plan_id,
        "workspace_id": workspace,
        "goal": cleaned_goal,
        "fan_out_intent": detect_fan_out_intent(cleaned_goal) or plan.mode == "fan_out",
        "mode": plan.mode,
        "plan": persisted["plan"],
        "plan_key_to_task_id": persisted["plan_key_to_task_id"],
        "tasks": list(tasks_by_id.values()),
        "runs": runs,
        "deferred": deferred,
        "receipt": {
            "receipt_id": receipt["receipt_id"],
            "type": receipt["kind"],
            "summary": (
                f"Lead materialized {len(persisted['tasks'])} tasks; "
                f"started {len(runs)} ready runs; deferred {len(deferred)}"
            ),
            "mode": plan.mode,
            "run_count": len(runs),
            "task_count": len(persisted["tasks"]),
        },
    }


__all__ = ["LeadFanOutError", "materialize_lead_fan_out"]
