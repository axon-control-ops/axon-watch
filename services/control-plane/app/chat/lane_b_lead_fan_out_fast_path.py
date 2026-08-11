"""Lead IDE assign-all → materialize fan-out (no Lane B Lead essay)."""

from __future__ import annotations

from typing import Any, Callable

from app.chat.lead_fan_out_transcript import format_lead_fan_out_agent_message
from app.workspace_agents.lead_fan_out import LeadFanOutError, materialize_lead_fan_out
from app.workspace_agents.lead_handoff_receipt import record_lead_handoff_run
from app.workspace_agents.lead_task_plan import (
    detect_fan_out_intent,
    is_employee_shift_retry_request,
)


def _format_fan_out_reply(
    *,
    lead_name: str,
    materialize: dict[str, Any],
    kick_started: int = 0,
) -> str:
    receipt = materialize.get("receipt") or {}
    summary = str(receipt.get("summary") or "").strip()
    notes = []
    if summary:
        notes.append(summary)
    else:
        notes.append(
            f"Materialized {len(materialize.get('tasks') or [])} tasks; "
            f"queued {len(materialize.get('runs') or [])} ready runs."
        )
    if kick_started > 0:
        notes.append(f"Dispatch kick started {kick_started} specialist run(s) just now.")
    else:
        notes.append(
            "Specialist runs are queued. The scheduler will retry explicit Lead handoffs "
            "on its watcher tick if a restart interrupts the first kick."
        )
    return format_lead_fan_out_agent_message(
        lead_name=lead_name,
        materialize=materialize,
        mode="fan_out",
        fleet_lines=notes,
        headline="I assigned the specialists via Lead fan-out.",
    )


def _kick_continuous_dispatch() -> int:
    try:
        from app.workspace_agents.scheduler import kick_lead_fan_out_dispatch

        started = kick_lead_fan_out_dispatch(starts_bound=3)
        return len(started or [])
    except Exception:
        return 0


def maybe_post_lead_fan_out_message(
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
    """When Lead hears assign-all intent, materialize fan-out instead of a Lane B essay."""
    role = str(employee_role or "").strip().lower()
    if is_employee_shift_retry_request(content):
        return None
    intent = detect_fan_out_intent(content)
    if composer_mode != "agent" or role != "lead" or not intent:
        return None

    try:
        materialize = materialize_lead_fan_out(
            workspace_id=workspace_id,
            goal=content,
            mode="fan_out",
            create_runs=True,
        )
    except LeadFanOutError:
        return None
    except Exception:
        return None

    kick_started = _kick_continuous_dispatch()

    plan_id = str(materialize.get("plan_id") or "").strip()
    handoff_run = record_lead_handoff_run(
        workspace_id=workspace_id,
        summary=content,
        detail=(
            f"Lead fan-out handoff completed"
            + (f" (plan {plan_id})" if plan_id else "")
            + "; specialists queued for dispatch"
        ),
    )
    handoff_run_id = str((handoff_run or {}).get("run_id") or "").strip() or None

    agent_content = _format_fan_out_reply(
        lead_name=lead_name.strip() or "Lead",
        materialize=materialize,
        kick_started=kick_started,
    )
    operator_message = save_message(
        {
            "message_id": new_message_id("message_operator"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": handoff_run_id,
            "role": "operator",
            "content": content,
            "created_at": created_at,
        }
    )
    operator_attachments = bind_attachments(str(operator_message["message_id"]))
    if operator_attachments:
        operator_message = {**operator_message, "attachments": operator_attachments}
    agent_message = save_message(
        {
            "message_id": new_message_id("message_agent"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": handoff_run_id,
            "role": "agent",
            "content": agent_content,
            "created_at": created_at,
        }
    )
    return {
        "thread_id": thread_id,
        "messages": [operator_message, agent_message],
        "run_id": handoff_run_id or "",
        "dispatched": True,
        "run": handoff_run,
        "streaming": False,
        "ui_action": None,
        "lead_fan_out": {
            "plan_id": materialize.get("plan_id"),
            "runs": materialize.get("runs") or [],
            "deferred": materialize.get("deferred") or [],
        },
    }


__all__ = ["maybe_post_lead_fan_out_message"]
