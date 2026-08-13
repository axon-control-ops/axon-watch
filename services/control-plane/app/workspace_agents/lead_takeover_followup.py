"""Lead follow-up task enqueue — sticky to controlling plan when present."""

from __future__ import annotations

import logging
from typing import Any

from app.persistence import task_store
from app.workspace_agents.lead_text import truncate_text

logger = logging.getLogger(__name__)


def should_suppress_redig_follow_up(
    *,
    lead_next: str,
    specialist_goal: str,
    has_controlling_plan: bool,
) -> bool:
    """Suppress ad-hoc follow-ups that only restart the same specialist dig."""
    if has_controlling_plan:
        return False
    next_line = (lead_next or "").strip()
    dig = (specialist_goal or "").strip()
    if not next_line or not dig:
        return False
    from app.workspace_agents.task_goal_overlap import goals_overlap

    return goals_overlap(next_line, dig)


def enqueue_lead_follow_up_task(
    *,
    workspace_id: str,
    employee_name: str,
    employee_role: str,
    lead_next: str,
    run_id: str,
    phase: str = "completed",
    blockers: str = "",
    specialist_goal: str = "",
    plan_id: str | None = None,
    task_id: str | None = None,
    dependencies: list[str] | None = None,
) -> dict[str, Any] | None:
    """Create an open Lead-owned follow-up sticky to the controlling plan when present."""
    workspace = workspace_id.strip()
    if not workspace:
        return None

    from app.workspace_agents.lead_plan_control import (
        controlling_lead_plan,
        extract_plan_id_from_goal,
        plan_marker,
        sticky_lead_follow_up_acceptance,
        sticky_lead_follow_up_goal,
    )

    plan = controlling_lead_plan(
        workspace,
        plan_id=plan_id,
        task_id=task_id,
    )
    if should_suppress_redig_follow_up(
        lead_next=lead_next,
        specialist_goal=specialist_goal,
        has_controlling_plan=plan is not None,
    ):
        logger.info(
            "lead follow-up suppressed (re-dig overlap) workspace=%s run=%s",
            workspace,
            run_id,
        )
        return None

    controlling_plan_id = str((plan or {}).get("plan_id") or "").strip()
    marker = plan_marker(controlling_plan_id) if controlling_plan_id else ""

    def _merge_follow_up_dependencies(existing: dict[str, Any]) -> list[str] | None:
        incoming = [str(item).strip() for item in (dependencies or []) if str(item).strip()]
        if not incoming:
            return None
        merged: list[str] = []
        seen: set[str] = set()
        for dep_id in incoming:
            if dep_id not in seen:
                seen.add(dep_id)
                merged.append(dep_id)
        for dep_id in existing.get("dependencies") or []:
            cleaned = str(dep_id or "").strip()
            if not cleaned or cleaned in seen:
                continue
            dep = task_store.get_task(cleaned)
            if dep is None:
                continue
            goal = str(dep.get("goal") or "")
            status = str(dep.get("status") or "").strip().lower()
            if goal.startswith("Verification after") and status != "completed":
                continue
            seen.add(cleaned)
            merged.append(cleaned)
        return merged

    for status in ("open", "leased"):
        for row in task_store.list_tasks(workspace_id=workspace, status=status, limit=100):
            if str(row.get("owner_role") or "").strip().lower() != "lead":
                continue
            goal = str(row.get("goal") or "")
            if run_id and run_id in goal:
                merged = _merge_follow_up_dependencies(row)
                if merged is not None and row.get("status") == "open":
                    try:
                        return task_store.refresh_task_dependencies(str(row["task_id"]), merged)
                    except task_store.TaskLedgerError:
                        return row
                return row
            if marker and marker in goal:
                merged = _merge_follow_up_dependencies(row)
                if merged is not None and row.get("status") == "open":
                    try:
                        return task_store.refresh_task_dependencies(str(row["task_id"]), merged)
                    except task_store.TaskLedgerError:
                        return row
                return row
            if controlling_plan_id and extract_plan_id_from_goal(goal) == controlling_plan_id:
                merged = _merge_follow_up_dependencies(row)
                if merged is not None and row.get("status") == "open":
                    try:
                        return task_store.refresh_task_dependencies(str(row["task_id"]), merged)
                    except task_store.TaskLedgerError:
                        return row
                return row

    name = (employee_name or employee_role or "specialist").strip()
    if plan is not None:
        goal_text = sticky_lead_follow_up_goal(
            plan=plan,
            employee_name=name,
            employee_role=employee_role,
            phase=phase,
            blockers=blockers,
            lead_next=lead_next,
            run_id=run_id,
        )
        acceptance = sticky_lead_follow_up_acceptance(plan=plan)
    else:
        next_line = truncate_text(
            lead_next or "Review specialist completion and decide next handoff.",
            max_len=220,
        )
        goal_text = (
            f"Lead follow-up after {name} ({employee_role}): {next_line} "
            f"[from run {run_id}]"
        )
        acceptance = (
            "Post a Lead decision: assign next specialist, approve ship, or ask the operator. "
            "Never invent status. Prefer verified receipts; consult official docs when needed. "
            "Suggest a concrete next step. End with Confidence: N/10."
        )
    try:
        return task_store.create_task(
            workspace_id=workspace,
            goal=goal_text,
            acceptance_criteria=acceptance,
            risk="normal",
            owner_role="lead",
            attempt_budget=2,
            dependencies=list(dependencies or []),
        )
    except task_store.TaskLedgerError as exc:
        logger.warning("lead follow-up task create failed: %s", exc)
        return None


__all__ = [
    "enqueue_lead_follow_up_task",
    "should_suppress_redig_follow_up",
]
