"""Lead IDE named-assign → refuse specialist work on the Lead thread."""

from __future__ import annotations

from typing import Any, Callable

from app.workspace_agents import build_company_roster
from app.workspace_agents.lead_task_plan import detect_fan_out_intent
from app.workspace_agents.named_assign_route import (
    match_named_assign_employee,
    named_assign_action_body,
)
from app.workspace_agents.teammate_route import normalize_teammate_role, roster_employees_from_company


def _create_named_handoff_task(
    *,
    workspace_id: str,
    specialist_name: str,
    owner_role: str,
    body: str,
) -> dict[str, Any]:
    from app.persistence import task_store
    from app.workspace_agents.operator_start_task import (
        OperatorStartTaskError,
        operator_start_task,
    )

    task = task_store.create_task(
        workspace_id=workspace_id,
        goal=f"Lead assigned to {specialist_name}: {body}",
        acceptance_criteria=(
            "Complete the Lead-routed specialist task with concrete receipts. "
            "Use the original operator goal as source of truth; if required screenshot "
            "context is missing from this thread, ask for it instead of guessing. "
            "Report changed files/tests and end with Confidence: N/10."
        ),
        risk="normal",
        owner_role=owner_role,
        attempt_budget=2,
    )
    try:
        started = operator_start_task(str(task["task_id"]))
        return {"task": started.get("task") or task, "run": started.get("run"), "started": True}
    except OperatorStartTaskError as exc:
        return {"task": task, "run": None, "started": False, "error": str(exc)}


def maybe_post_lead_named_assign_message(
    *,
    workspace_id: str,
    content: str,
    thread_id: str,
    employee_role: str | None,
    lead_name: str,
    composer_mode: str,
    created_at: str,
    save_message: Callable[[dict[str, Any]], dict[str, Any]],
    new_message_id: Callable[[str], str],
    bind_attachments: Callable[[str], list[dict[str, object]]],
) -> dict[str, object] | None:
    """When Lead is told to assign a named teammate, ack-and-stop (no Lane B essay)."""
    role = str(employee_role or "").strip().lower()
    if composer_mode != "agent" or role != "lead":
        return None
    if detect_fan_out_intent(content):
        return None

    try:
        company = build_company_roster(workspace_id)
        roster = roster_employees_from_company({"company": company})
    except Exception:
        return None

    named = match_named_assign_employee(content, roster)
    if named is None:
        return None
    if normalize_teammate_role(named.role) == "lead":
        return None

    action_body = named_assign_action_body(content, named.name)

    operator_message = save_message(
        {
            "message_id": new_message_id("message_operator"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": None,
            "role": "operator",
            "content": content,
            "created_at": created_at,
        }
    )
    operator_attachments = bind_attachments(str(operator_message["message_id"]))
    if operator_attachments:
        operator_message = {**operator_message, "attachments": operator_attachments}
    handoff_result: dict[str, Any] | None = None
    if action_body:
        handoff_result = _create_named_handoff_task(
            workspace_id=workspace_id,
            specialist_name=named.name,
            owner_role=normalize_teammate_role(named.role),
            body=action_body,
        )
        task = handoff_result.get("task") or {}
        run = handoff_result.get("run") or {}
        task_id = str(task.get("task_id") or "").strip()
        run_id = str(run.get("run_id") or "").strip()
        started = bool(handoff_result.get("started"))
        agent_content = "\n".join(
            [
                f"Sir King — routed a concrete Lead handoff to {named.name} ({named.role_label or named.role}).",
                "",
                f"Task: {task_id or 'created'}" + (f" / Run: {run_id}" if run_id else ""),
                f"Status: {'started' if started else 'queued'}",
                "",
                f"Assignment body: {action_body}",
                "",
                f"— {lead_name.strip() or 'Lead'}",
            ]
        )
    else:
        agent_content = "\n".join(
            [
                f"Sir King — I did not route {named.name} yet because the message only says to route “the task” and I cannot find a prior concrete operator ask in this thread.",
                "",
                f"Please send the exact goal/acceptance criteria, or paste the original ask, and I will create the handoff.",
                f"— {lead_name.strip() or 'Lead'}",
            ]
        )
    system_message = save_message(
        {
            "message_id": new_message_id("message_system"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": str(((handoff_result or {}).get("run") or {}).get("run_id") or "") or None,
            "role": "system",
            "content": (
                f"Named assign to {named.name} detected on Lead thread — "
                "created a concrete specialist handoff when a task body was available."
            ),
            "created_at": created_at,
        }
    )
    agent_message = save_message(
        {
            "message_id": new_message_id("message_agent"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": str(((handoff_result or {}).get("run") or {}).get("run_id") or "") or None,
            "role": "agent",
            "content": agent_content,
            "created_at": created_at,
        }
    )
    response_run_id = str(((handoff_result or {}).get("run") or {}).get("run_id") or "")
    return {
        "thread_id": thread_id,
        "messages": [operator_message, system_message, agent_message],
        "run_id": response_run_id,
        "dispatched": bool(handoff_result and handoff_result.get("started")),
        "run": (handoff_result or {}).get("run"),
        "streaming": False,
        "ui_action": None,
        "named_assign": {
            "employee_id": named.employee_id,
            "employee_name": named.name,
            "employee_role": named.role,
            "task_id": str(((handoff_result or {}).get("task") or {}).get("task_id") or ""),
        },
    }


__all__ = ["maybe_post_lead_named_assign_message"]
