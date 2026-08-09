"""Lead fan-out — plan → ledger tasks → ready specialist runs (Gate 5)."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any
from uuid import uuid4

from app.persistence import chat_store, task_store
from app.runs.service import append_run_execution_receipt, create_run
from app.workspace_agents import build_company_roster
from app.workspace_agents.assignment_messages import assignment_card, employee_display_name
from app.workspace_agents import lead_plan_store
from app.workspace_agents.lead_task_persist import persist_lead_task_plan
from app.workspace_agents.lead_task_plan import (
    LeadTaskPlan,
    LeadTaskPlanItem,
    LeadPlanRosterMember,
    PlanMode,
    detect_fan_out_intent,
    topo_order,
)
from app.workspace_agents.lead_plan_model import resolve_lead_task_plan
from app.workspace_agents.task_goal_overlap import (
    goals_overlap,
    normalize_goal_core,
    token_set,
)


class LeadFanOutError(ValueError):
    """Operator-facing fan-out / plan materialize failure."""


_TASK_ID_RE = re.compile(r"\btask-[a-z0-9]{12,}\b", re.I)


def _extract_task_ids(text: str) -> list[str]:
    seen: set[str] = set()
    task_ids: list[str] = []
    for match in _TASK_ID_RE.finditer(text or ""):
        task_id = match.group(0)
        key = task_id.lower()
        if key in seen:
            continue
        seen.add(key)
        task_ids.append(task_id)
    return task_ids


def supersede_stale_queue_for_new_lead_goal(
    *,
    workspace_id: str,
    goal: str,
    exclude_task_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Cancel older open/leased specialist tasks that overlap this Lead ask.

    Prevents retry spam ("Please confirm if we did this job…") from filling the
    fleet queue so Leads cannot get new work started.
    """
    workspace = workspace_id.strip()
    core = normalize_goal_core(goal)
    if not workspace or len(core) < 12:
        return []
    core_tokens = token_set(core)
    if len(core_tokens) < 2:
        return []
    excluded = {
        str(task_id).strip()
        for task_id in (exclude_task_ids or set())
        if str(task_id).strip()
    }
    cancelled: list[dict[str, Any]] = []
    for record in task_store.list_tasks(workspace_id=workspace, limit=500):
        status = str(record.get("status") or "").strip().lower()
        if status not in {"open", "leased"}:
            continue
        other_goal = str(record.get("goal") or "")
        if not goals_overlap(goal, other_goal, threshold=0.45):
            continue
        task_id = str(record.get("task_id") or "").strip()
        if not task_id:
            continue
        if task_id in excluded:
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


def employee_for_role(workspace_id: str, role: str) -> dict[str, Any] | None:
    """Public roster lookup by role (Lead voice / takeover / check-in)."""
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


# Compat alias — prefer employee_for_role at new call sites.
_employee_for_role = employee_for_role


def _employee_id_for_role(workspace_id: str, role: str) -> str | None:
    employee = employee_for_role(workspace_id, role)
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
    assignee = employee_for_role(workspace_id, owner_role)
    lead = employee_for_role(workspace_id, "lead")
    assignee_name = employee_display_name(assignee, owner_role)
    lead_name = employee_display_name(lead, "lead")
    lead_employee_id = str((lead or {}).get("employee_id") or "").strip() or None
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
    # Compact human assignment card only — raw task/run ids stay in the receipt line.
    # Lead keeps a full summary on their own thread; run receipts stay on the ledger.
    chat_store.save_message(
        {
            "message_id": f"message_agent_{uuid4().hex}",
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": run_id,
            "role": "agent",
            "content": assignment_card(
                assignee_name=assignee_name,
                assignee_role=owner_role,
                goal=goal_line or str(task_id),
                task_id=task_id,
                run_id=run_id,
                state="queued",
                lead_name=lead_name,
            ),
            "speaker_name": lead_name,
            "speaker_role": "lead",
            "speaker_employee_id": lead_employee_id,
            "created_at": created_at,
        }
    )
    return thread_id


def _build_existing_task_plan(
    *,
    goal: str,
    tasks: list[dict[str, Any]],
) -> tuple[LeadTaskPlan, dict[str, str]]:
    plan_key_to_task_id: dict[str, str] = {}
    key_by_task_id: dict[str, str] = {}
    items: list[LeadTaskPlanItem] = []
    for index, task in enumerate(tasks, start=1):
        task_id = str(task.get("task_id") or "").strip()
        owner_role = str(task.get("owner_role") or "").strip().lower() or "watcher"
        plan_key = f"task-{index:02d}-{owner_role}"
        plan_key_to_task_id[plan_key] = task_id
        key_by_task_id[task_id] = plan_key

    for index, task in enumerate(tasks, start=1):
        task_id = str(task.get("task_id") or "").strip()
        owner_role = str(task.get("owner_role") or "").strip().lower() or "watcher"
        plan_key = key_by_task_id[task_id]
        dependencies = [
            key_by_task_id[str(dep).strip()]
            for dep in task.get("dependencies") or []
            if str(dep).strip() in key_by_task_id
        ]
        items.append(
            LeadTaskPlanItem(
                plan_key=plan_key,
                goal=str(task.get("goal") or goal).strip(),
                owner_role=owner_role,
                acceptance_criteria=str(task.get("acceptance_criteria") or "").strip(),
                dependencies=dependencies,
                risk=str(task.get("risk") or "normal").strip() or "normal",
                exclusive_paths=list(task.get("exclusive_paths") or []),
                allowed_paths=list(task.get("allowed_paths") or []),
            )
        )

    return (
        LeadTaskPlan(
            goal=goal,
            mode="fan_out",
            items=items,
            ordered_keys=topo_order(items),
            ambiguous=False,
        ),
        plan_key_to_task_id,
    )


def _create_ready_run_for_task(
    *,
    workspace_id: str,
    task_id: str,
    plan_key: str,
    owner_role: str,
    mode: str,
    cleaned_goal: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    fresh = task_store.get_task(task_id)
    if fresh is None:
        return None, None, {
            "task_id": task_id,
            "plan_key": plan_key,
            "owner_role": owner_role,
            "reason": "task_not_found",
        }
    if not _deps_completed(fresh):
        return None, fresh, {
            "task_id": task_id,
            "plan_key": plan_key,
            "owner_role": fresh.get("owner_role"),
            "reason": "dependencies_incomplete",
        }
    role = str(fresh.get("owner_role") or owner_role).strip().lower()
    holder = f"lead-fan-out-{workspace_id}-{role}"
    try:
        leased = task_store.lease_task(task_id, lease_holder=holder)
    except task_store.TaskLedgerError as exc:
        return None, fresh, {
            "task_id": task_id,
            "plan_key": plan_key,
            "owner_role": role,
            "reason": str(exc),
        }
    summary = f"{role}: {str(leased.get('goal') or cleaned_goal)[:120]}"
    run = create_run(
        workspace_id=workspace_id,
        mode="agent",
        summary=summary,
        detail=f"Lead fan-out ({mode}) plan_key={plan_key} task={task_id}",
        employee_role=role,
        task_id=task_id,
        require_leased_task=True,
        enter_execution=False,
    )
    append_run_execution_receipt(
        str(run["run_id"]),
        receipt_type="lead_fan_out_assigned",
        receipt_summary=f"Lead assigned {role} task {task_id} ({plan_key})",
        actor="lead_planner",
    )
    thread_id = _post_assignment_to_employee_thread(
        workspace_id=workspace_id,
        owner_role=role,
        run_id=str(run["run_id"]),
        task_id=task_id,
        goal=str(leased.get("goal") or cleaned_goal),
    )
    return (
        {
            "run_id": run["run_id"],
            "task_id": task_id,
            "plan_key": plan_key,
            "owner_role": role,
            "phase": run.get("phase"),
            "thread_id": thread_id,
        },
        task_store.get_task(task_id) or leased,
        None,
    )


def _materialize_existing_task_ids(
    *,
    workspace_id: str,
    goal: str,
    task_ids: list[str],
    create_runs: bool,
    supersedes_plan_id: str | None,
) -> dict[str, Any]:
    workspace = workspace_id.strip()
    records: list[dict[str, Any]] = []
    missing: list[str] = []
    wrong_workspace: list[str] = []
    for task_id in task_ids:
        record = task_store.get_task(task_id)
        if record is None:
            missing.append(task_id)
            continue
        if str(record.get("workspace_id") or "").strip() != workspace:
            wrong_workspace.append(task_id)
            continue
        records.append(record)
    if missing:
        raise LeadFanOutError(f"task not found: {', '.join(missing)}")
    if wrong_workspace:
        raise LeadFanOutError(
            f"task workspace mismatch: {', '.join(wrong_workspace)}"
        )
    if not records:
        raise LeadFanOutError("no matching task IDs found")

    explicit_ids = {str(record["task_id"]) for record in records}
    superseded = supersede_stale_queue_for_new_lead_goal(
        workspace_id=workspace,
        goal=goal,
        exclude_task_ids=explicit_ids,
    )
    try:
        from app.workspace_agents.task_duplicate_cleanup import (
            reconcile_workspace_waiting_duplicates,
        )

        reconcile_workspace_waiting_duplicates(workspace_id=workspace)
    except Exception:  # noqa: BLE001 — never block Lead materialize on cleanup
        pass

    plan, plan_key_to_task_id = _build_existing_task_plan(goal=goal, tasks=records)
    stored_plan = lead_plan_store.persist_plan(
        workspace_id=workspace,
        plan=plan.to_dict(),
        plan_key_to_task_id=plan_key_to_task_id,
        supersedes_plan_id=supersedes_plan_id,
    )
    plan_id = str(stored_plan["plan_id"])
    tasks_by_id = {str(record["task_id"]): record for record in records}
    runs: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []

    if create_runs:
        for plan_key in plan.ordered_keys:
            task_id = plan_key_to_task_id[plan_key]
            owner_role = (
                str((tasks_by_id.get(task_id) or {}).get("owner_role") or "")
                .strip()
                .lower()
            )
            run, task, defer = _create_ready_run_for_task(
                workspace_id=workspace,
                task_id=task_id,
                plan_key=plan_key,
                owner_role=owner_role,
                mode=plan.mode,
                cleaned_goal=goal,
            )
            if task is not None:
                tasks_by_id[task_id] = task
            if run is not None:
                runs.append(run)
            if defer is not None:
                deferred.append(defer)

    receipt = lead_plan_store.append_receipt(
        plan_id=plan_id,
        workspace_id=workspace,
        kind="lead_fan_out_materialized",
        payload={
            "mode": plan.mode,
            "task_count": len(records),
            "run_ids": [str(run["run_id"]) for run in runs],
            "deferred_task_ids": [str(row["task_id"]) for row in deferred],
            "thread_ids": [
                str(run["thread_id"]) for run in runs if run.get("thread_id")
            ],
            "explicit_task_ids": list(task_ids),
        },
    )
    return {
        "plan_id": plan_id,
        "workspace_id": workspace,
        "goal": goal,
        "fan_out_intent": True,
        "mode": plan.mode,
        "plan": plan.to_dict(),
        "plan_key_to_task_id": plan_key_to_task_id,
        "tasks": list(tasks_by_id.values()),
        "runs": runs,
        "deferred": deferred,
        "superseded_tasks": superseded,
        "receipt": {
            "receipt_id": receipt["receipt_id"],
            "type": receipt["kind"],
            "summary": (
                f"Lead materialized {len(records)} existing task(s); "
                f"queued {len(runs)} ready runs; deferred {len(deferred)}"
                + (
                    f"; superseded {len(superseded)} stale queue task(s)"
                    if superseded
                    else ""
                )
            ),
            "mode": plan.mode,
            "run_count": len(runs),
            "task_count": len(records),
        },
    }


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

    explicit_task_ids = _extract_task_ids(cleaned_goal)
    if explicit_task_ids:
        return _materialize_existing_task_ids(
            workspace_id=workspace,
            goal=cleaned_goal,
            task_ids=explicit_task_ids,
            create_runs=create_runs,
            supersedes_plan_id=supersedes_plan_id,
        )

    superseded = supersede_stale_queue_for_new_lead_goal(
        workspace_id=workspace,
        goal=cleaned_goal,
    )
    try:
        from app.workspace_agents.task_duplicate_cleanup import (
            reconcile_workspace_waiting_duplicates,
        )

        reconcile_workspace_waiting_duplicates(workspace_id=workspace)
    except Exception:  # noqa: BLE001 — never block Lead materialize on cleanup
        pass

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
            run, task, defer = _create_ready_run_for_task(
                workspace_id=workspace,
                task_id=task_id,
                plan_key=str(row.get("plan_key") or ""),
                owner_role=owner_role,
                mode=plan.mode,
                cleaned_goal=cleaned_goal,
            )
            if task is not None:
                tasks_by_id[task_id] = task
            if run is not None:
                runs.append(run)
            if defer is not None:
                deferred.append(defer)

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
