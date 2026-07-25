"""Lead fan-out — plan → ledger tasks → ready specialist runs (Gate 5)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.persistence import chat_store, task_store
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


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


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


def _employee_id_for_role(workspace_id: str, role: str) -> str | None:
    company = build_company_roster(workspace_id)
    rows = company.get("employees") if isinstance(company, dict) else None
    if not isinstance(rows, list):
        return None
    want = role.strip().lower()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("role") or "").strip().lower() == want:
            employee_id = str(row.get("employee_id") or "").strip()
            return employee_id or None
    return None


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


def _post_assignment_to_employee_thread(
    *,
    workspace_id: str,
    owner_role: str,
    run_id: str,
    task_id: str,
    goal: str,
) -> str | None:
    """Surface fan-out assignment in the specialist IDE thread (not silent busy)."""
    employee_id = _employee_id_for_role(workspace_id, owner_role)
    if not employee_id:
        return None
    created_at = _utc_now_iso()
    thread = chat_store.find_thread_for_employee(
        workspace_id,
        employee_id=employee_id,
        thread_kind="ide",
    )
    if thread is None:
        name = owner_role.replace("_", " ").title()
        thread = chat_store.create_thread(
            workspace_id=workspace_id,
            run_id=run_id,
            created_at=created_at,
            thread_kind="ide",
            title=f"{name} · assigned",
            employee_id=employee_id,
            employee_role=owner_role,
        )
    thread_id = str(thread["thread_id"])
    goal_line = " ".join(str(goal or "").split())
    if len(goal_line) > 220:
        goal_line = f"{goal_line[:219].rstrip()}…"
    chat_store.save_message(
        {
            "message_id": f"message_system_{uuid4().hex}",
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": run_id,
            "role": "system",
            "content": (
                f"Lead fan-out assigned task {task_id} → run {run_id} "
                f"(queued — waiting for worker dispatch)."
            ),
            "created_at": created_at,
        }
    )
    chat_store.save_message(
        {
            "message_id": f"message_agent_{uuid4().hex}",
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": run_id,
            "role": "agent",
            "content": (
                f"Assigned by Lead fan-out.\n"
                f"Goal: {goal_line or '(no goal text)'}\n"
                f"Status: queued until continuous worker dispatch starts Lane B. "
                f"Open this thread after dispatch to follow the shift transcript."
            ),
            "created_at": created_at,
        }
    )
    return thread_id


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
    Ready runs stay **queued** (not fake-executing) so the operator sees assignment
    in specialist threads and the scheduler can dispatch without slot deadlock.
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
                enter_execution=False,
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
            thread_id = _post_assignment_to_employee_thread(
                workspace_id=workspace,
                owner_role=owner_role,
                run_id=str(run["run_id"]),
                task_id=task_id,
                goal=str(leased.get("goal") or cleaned_goal),
            )
            runs.append(
                {
                    "run_id": run["run_id"],
                    "task_id": task_id,
                    "plan_key": row.get("plan_key"),
                    "owner_role": owner_role,
                    "phase": run.get("phase"),
                    "thread_id": thread_id,
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
            "thread_ids": [
                str(run["thread_id"]) for run in runs if run.get("thread_id")
            ],
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
                f"queued {len(runs)} ready runs; deferred {len(deferred)}"
            ),
            "mode": plan.mode,
            "run_count": len(runs),
            "task_count": len(persisted["tasks"]),
        },
    }


__all__ = ["LeadFanOutError", "materialize_lead_fan_out"]
