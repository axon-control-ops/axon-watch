"""Lead IDE multi-domain ask → materialize decompose (no Lane B essay)."""

from __future__ import annotations

import threading
from typing import Any, Callable

from app.workspace_agents import build_company_roster
from app.workspace_agents.lead_fan_out import LeadFanOutError, materialize_lead_fan_out
from app.workspace_agents.lead_plan_model import resolve_lead_task_plan
from app.workspace_agents.lead_task_plan import (
    LeadPlanRosterMember,
    detect_fan_out_intent,
    should_lead_decompose_dispatch,
)


def _roster_members(workspace_id: str) -> list[LeadPlanRosterMember]:
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


def _format_decompose_reply(
    *,
    lead_name: str,
    materialize: dict[str, Any],
) -> str:
    runs = list(materialize.get("runs") or [])
    deferred = list(materialize.get("deferred") or [])
    tasks = list(materialize.get("tasks") or [])
    lines = [
        f"Sir King — I decomposed the work and assigned specialists "
        f"(plan `{materialize.get('plan_id')}`).",
        "",
    ]
    if tasks:
        lines.append("Assignments:")
        for task in tasks:
            role = str(task.get("owner_role") or "?").strip()
            goal = " ".join(str(task.get("goal") or "").split())
            if len(goal) > 140:
                goal = f"{goal[:139].rstrip()}…"
            lines.append(f"- {role}: {goal or '(no goal)'}")
        lines.append("")
    if runs:
        lines.append(f"Queued runs: {len(runs)}")
        lines.append("")
    if deferred:
        lines.append(f"Deferred (dependencies): {len(deferred)}")
        lines.append("")
    lines.append(
        "I did not do that specialist work on this Lead thread. "
        "Open each specialist thread after continuous dispatch starts. "
        f"— {lead_name.strip() or 'Lead'}"
    )
    return "\n".join(lines)


def _kick_continuous_dispatch() -> None:
    try:
        from app.workspace_agents.scheduler import run_continuous_worker_tick

        run_continuous_worker_tick()
    except Exception:
        pass


def maybe_post_lead_decompose_message(
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
    """When Lead hears a multi-domain implement ask, materialize decompose plan."""
    role = str(employee_role or "").strip().lower()
    if composer_mode != "agent" or role != "lead":
        return None
    if detect_fan_out_intent(content):
        return None

    try:
        roster = _roster_members(workspace_id)
        preview = resolve_lead_task_plan(
            goal=content,
            roster=roster,
            mode="decompose",
            workspace_id=workspace_id,
            use_model=False,
        )
    except Exception:
        return None

    if not should_lead_decompose_dispatch(preview):
        return None

    try:
        materialize = materialize_lead_fan_out(
            workspace_id=workspace_id,
            goal=content,
            mode="decompose",
            create_runs=True,
            use_model=True,
        )
    except LeadFanOutError:
        return None
    except Exception:
        return None

    threading.Thread(
        target=_kick_continuous_dispatch,
        daemon=True,
        name="lead-decompose-dispatch-kick",
    ).start()

    agent_content = _format_decompose_reply(
        lead_name=lead_name.strip() or "Lead",
        materialize=materialize,
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
                "Lead decompose materialized; specialist runs queued for continuous dispatch "
                "(no Lane B Lead turn)."
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
        "lead_decompose": {
            "plan_id": materialize.get("plan_id"),
            "mode": materialize.get("mode"),
            "runs": materialize.get("runs") or [],
            "deferred": materialize.get("deferred") or [],
            "tasks": materialize.get("tasks") or [],
        },
    }


__all__ = ["maybe_post_lead_decompose_message"]
