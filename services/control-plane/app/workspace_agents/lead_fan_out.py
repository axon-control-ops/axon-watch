"""Lead fan-out — plan → ledger tasks → ready specialist runs (Gate 5)."""

from __future__ import annotations

import re
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
    detect_fan_out_intent,
)
from app.workspace_agents.lead_plan_model import resolve_lead_task_plan


class LeadFanOutError(ValueError):
    """Operator-facing fan-out / plan materialize failure."""


_CONFIRM_PREFIX_RE = re.compile(
    r"^\s*please\s+confirm\s+if\s+we\s+did\s+this\s+job\s*['\"]?",
    re.I,
)


def _normalize_goal_core(goal: str) -> str:
    cleaned = " ".join(str(goal or "").strip().split()).lower()
    cleaned = _CONFIRM_PREFIX_RE.sub("", cleaned).strip(" '\"")
    return cleaned


def _token_set(text: str) -> set[str]:
    tokens: set[str] = set()
    for tok in re.findall(r"[a-z0-9]{3,}", text.lower()):
        tokens.add(tok)
        if len(tok) > 4 and tok.endswith("s"):
            tokens.add(tok[:-1])
    return tokens


def supersede_stale_queue_for_new_lead_goal(
    *,
    workspace_id: str,
    goal: str,
) -> list[dict[str, Any]]:
    """Cancel older open/leased specialist tasks that overlap this Lead ask.

    Prevents retry spam ("Please confirm if we did this job…") from filling the
    fleet queue so Leads cannot get new work started.
    """
    workspace = workspace_id.strip()
    core = _normalize_goal_core(goal)
    if not workspace or len(core) < 12:
        return []
    core_tokens = _token_set(core)
    if len(core_tokens) < 2:
        return []
    cancelled: list[dict[str, Any]] = []
    for record in task_store.list_tasks(workspace_id=workspace, limit=500):
        status = str(record.get("status") or "").strip().lower()
        if status not in {"open", "leased"}:
            continue
        other_core = _normalize_goal_core(str(record.get("goal") or ""))
        if len(other_core) < 12:
            continue
        other_tokens = _token_set(other_core)
        if not other_tokens:
            continue
        overlap = len(core_tokens & other_tokens) / float(min(len(core_tokens), len(other_tokens)))
        nested = core in other_core or other_core in core
        if not nested and overlap < 0.45:
            continue
        task_id = str(record.get("task_id") or "").strip()
        if not task_id:
            continue
        try:
            row = task_store.cancel_task(
                task_id,
                terminal_outcome="superseded by newer Lead ask",
            )
        except task_store.TaskLedgerError:
            continue
        run_id = str(row.get("run_id") or record.get("run_id") or "").strip()
        if run_id:
            try:
                from app.runs.restart_reconcile import interrupt_run_on_restart

                interrupt_run_on_restart(run_id)
            except Exception:  # noqa: BLE001
                pass
        cancelled.append(row)
    return cancelled


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


def _employee_for_role(workspace_id: str, role: str) -> dict[str, Any] | None:
    company = build_company_roster(workspace_id)
    rows = company.get("employees") if isinstance(company, dict) else None
    if not isinstance(rows, list):
        return None
    want = role.strip().lower()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("role") or "").strip().lower() == want:
            return row
    return None


def _employee_id_for_role(workspace_id: str, role: str) -> str | None:
    employee = _employee_for_role(workspace_id, role)
    if employee is None:
        return None
    employee_id = str(employee.get("employee_id") or "").strip()
    return employee_id or None


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
    goal_line = " ".join(str(goal or "").strip().split())
    if len(goal_line) > 160:
        goal_line = f"{goal_line[:159].rstrip()}…"
    # Compact chip only — SYSTEM queue essays clutter the specialist dock.
    # Lead keeps a full summary on their own thread; run receipts stay on the ledger.
    chat_store.save_message(
        {
            "message_id": f"message_agent_{uuid4().hex}",
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": run_id,
            "role": "agent",
            "content": f"Queued for dispatch · {goal_line or f'task `{task_id}`'}",
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
    use_model: bool = True,
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

    superseded = supersede_stale_queue_for_new_lead_goal(
        workspace_id=workspace,
        goal=cleaned_goal,
    )

    roster = _roster_from_company(workspace)
    if not roster:
        raise LeadFanOutError(f"no company roster for workspace {workspace}")

    try:
        plan = resolve_lead_task_plan(
            goal=cleaned_goal,
            roster=roster,
            mode=mode,
            workspace_id=workspace,
            use_model=use_model,
        )
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
        "superseded_tasks": superseded,
        "receipt": {
            "receipt_id": receipt["receipt_id"],
            "type": receipt["kind"],
            "summary": (
                f"Lead materialized {len(persisted['tasks'])} tasks; "
                f"queued {len(runs)} ready runs; deferred {len(deferred)}"
                + (
                    f"; superseded {len(superseded)} stale queue task(s)"
                    if superseded
                    else ""
                )
            ),
            "mode": plan.mode,
            "run_count": len(runs),
            "task_count": len(persisted["tasks"]),
        },
    }


__all__ = [
    "LeadFanOutError",
    "materialize_lead_fan_out",
    "supersede_stale_queue_for_new_lead_goal",
]
