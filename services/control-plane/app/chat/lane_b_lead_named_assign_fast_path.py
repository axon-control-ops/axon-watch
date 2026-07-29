"""Lead IDE named-assign → refuse specialist work on the Lead thread."""

from __future__ import annotations

from typing import Any, Callable

from app.workspace_agents import build_company_roster
from app.workspace_agents.named_assign_route import match_named_assign_employee
from app.workspace_agents.teammate_route import (
    normalize_teammate_role,
    roster_employees_from_company,
)


def _format_named_assign_ack(*, lead_name: str, specialist_name: str, role_label: str) -> str:
    specialist = specialist_name.strip() or "that specialist"
    label = role_label.strip() or "specialist"
    return "\n".join(
        [
            f"Sir King — assigning {specialist} ({label}).",
            "",
            f"Open {specialist}'s thread for the live shift. "
            "I will not do that specialist work on this Lead thread or role-play their receipts.",
            f"— {lead_name.strip() or 'Lead'}",
        ]
    )


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

    agent_content = _format_named_assign_ack(
        lead_name=lead_name,
        specialist_name=named.name,
        role_label=named.role_label or named.role,
    )
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
    system_message = save_message(
        {
            "message_id": new_message_id("message_system"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": None,
            "role": "system",
            "content": (
                f"Named assign to {named.name} detected on Lead thread — "
                "no Lane B Lead turn; open the specialist thread to dispatch."
            ),
            "created_at": created_at,
        }
    )
    agent_message = save_message(
        {
            "message_id": new_message_id("message_agent"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": None,
            "role": "agent",
            "content": agent_content,
            "created_at": created_at,
        }
    )
    return {
        "thread_id": thread_id,
        "messages": [operator_message, system_message, agent_message],
        "run_id": "",
        "dispatched": True,
        "run": None,
        "streaming": False,
        "ui_action": None,
        "named_assign": {
            "employee_id": named.employee_id,
            "employee_name": named.name,
            "employee_role": named.role,
        },
    }


__all__ = ["maybe_post_lead_named_assign_message"]
