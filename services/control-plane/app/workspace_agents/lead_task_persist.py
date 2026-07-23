"""Persist a LeadTaskPlan into the Gate 4 workspace_tasks ledger."""

from __future__ import annotations

from typing import Any

from app.persistence import task_store
from app.workspace_agents import lead_plan_store
from app.workspace_agents.lead_task_plan import LeadTaskPlan


def persist_lead_task_plan(
    *,
    workspace_id: str,
    plan: LeadTaskPlan,
    supersedes_plan_id: str | None = None,
) -> dict[str, Any]:
    """Create ledger tasks for each plan item; map plan_key deps → task_id deps.

    Tasks are inserted in ``ordered_keys`` order so dependency rows exist before
    dependents reference them.
    """
    workspace = workspace_id.strip()
    if not workspace:
        raise task_store.TaskLedgerError("workspace_id is required")

    by_key = {item.plan_key: item for item in plan.items}
    plan_key_to_task_id: dict[str, str] = {}
    tasks: list[dict[str, Any]] = []

    for plan_key in plan.ordered_keys:
        item = by_key[plan_key]
        dep_task_ids = [
            plan_key_to_task_id[dep]
            for dep in item.dependencies
            if dep in plan_key_to_task_id
        ]
        created = task_store.create_task(
            workspace_id=workspace,
            goal=item.goal,
            acceptance_criteria=item.acceptance_criteria,
            risk=item.risk,
            owner_role=item.owner_role,
            dependencies=dep_task_ids,
            exclusive_paths=item.exclusive_paths,
            assignee_name=item.assignee_name,
            attachment_ids=item.attachment_ids,
            source_message_id=item.source_message_id,
            output_artifacts=item.output_artifacts,
        )
        plan_key_to_task_id[plan_key] = str(created["task_id"])
        tasks.append(
            {
                **created,
                "plan_key": plan_key,
                "exclusive_paths": list(item.exclusive_paths),
                "assignee_name": item.assignee_name,
                "attachment_ids": list(item.attachment_ids),
                "source_message_id": item.source_message_id,
                "output_artifacts": list(item.output_artifacts),
            }
        )

    serialized_plan = plan.to_dict()
    stored_plan = lead_plan_store.persist_plan(
        workspace_id=workspace,
        plan=serialized_plan,
        plan_key_to_task_id=plan_key_to_task_id,
        supersedes_plan_id=supersedes_plan_id,
    )
    return {
        "plan_id": stored_plan["plan_id"],
        "workspace_id": workspace,
        "plan": serialized_plan,
        "plan_key_to_task_id": plan_key_to_task_id,
        "tasks": tasks,
    }


__all__ = ["persist_lead_task_plan"]
