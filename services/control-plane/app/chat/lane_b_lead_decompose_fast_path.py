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
    is_employee_shift_retry_request,
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


def _fleet_status_lines(*, kick_started: int, queued_run_count: int) -> list[str]:
    """Explain why specialists may not start immediately after decompose."""
    try:
        from app.workspace_agents.scheduler import (
            max_active_executing,
            max_starts_per_tick,
            scheduler_enabled,
            tick_interval_seconds,
            _executing_run_count,
        )

        enabled = scheduler_enabled()
        executing = _executing_run_count()
        active_bound = max_active_executing()
        starts = max_starts_per_tick()
        interval = int(tick_interval_seconds())
    except Exception:
        if kick_started > 0:
            return [f"Dispatch kick started {kick_started} specialist run(s)."]
        return [
            "Specialist runs are queued for continuous dispatch. "
            "Open each specialist thread when their shift starts."
        ]

    lines: list[str] = []
    if not enabled:
        lines.append(
            "Continuous workers are OFF — specialist runs stay queued until you "
            "enable the worker scheduler (Mission Control / Full)."
        )
        return lines

    lines.append(f"Fleet: {executing}/{active_bound} workers busy · up to {starts} start(s) per ~{interval}s tick.")
    if kick_started > 0:
        lines.append(f"Dispatch kick started {kick_started} specialist run(s) just now.")
    elif queued_run_count > 0 and executing >= active_bound:
        lines.append(
            f"All worker slots are full — your {queued_run_count} queued run(s) will start "
            "as soon as a slot frees (not stuck; waiting on capacity)."
        )
    elif queued_run_count > 0:
        lines.append(
            f"{queued_run_count} specialist run(s) are queued; dispatch kick requested "
            "(will start on the next free slot)."
        )
    lines.append(
        "I did not do that specialist work on this Lead thread — open each specialist "
        "thread after their dispatch starts."
    )
    return lines


def _format_decompose_reply(
    *,
    lead_name: str,
    materialize: dict[str, Any],
    kick_started: int = 0,
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
    lines.extend(_fleet_status_lines(kick_started=kick_started, queued_run_count=len(runs)))
    superseded = list(materialize.get("superseded_tasks") or [])
    if superseded:
        lines.append(
            f"Cleared {len(superseded)} overlapping stale queue task(s) so this handoff can move."
        )
    lines.append(f"— {lead_name.strip() or 'Lead'}")
    return "\n".join(lines)


def _kick_continuous_dispatch() -> int:
    """Kick specialists with a slightly elevated start budget when slots are free."""
    try:
        from app.workspace_agents.scheduler import (
            max_active_executing,
            max_starts_per_tick,
            run_continuous_worker_tick,
            _executing_run_count,
        )

        free = max(0, max_active_executing() - _executing_run_count())
        # Lead handoffs should start more than one specialist when capacity allows.
        override = max(max_starts_per_tick(), min(3, free or max_starts_per_tick()))
        started = run_continuous_worker_tick(starts_bound_override=override)
        return len(started or [])
    except Exception:
        return 0


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
    if is_employee_shift_retry_request(content):
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

    # Background kick with elevated start budget when slots are free.
    threading.Thread(
        target=_kick_continuous_dispatch,
        daemon=True,
        name="lead-decompose-dispatch-kick",
    ).start()

    agent_content = _format_decompose_reply(
        lead_name=lead_name.strip() or "Lead",
        materialize=materialize,
        kick_started=0,
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
