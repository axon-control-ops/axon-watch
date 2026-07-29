"""Lead IDE assign-all → materialize fan-out (no Lane B Lead essay)."""

from __future__ import annotations

import threading
from typing import Any, Callable

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
) -> str:
    runs = list(materialize.get("runs") or [])
    deferred = list(materialize.get("deferred") or [])
    receipt = materialize.get("receipt") or {}
    lines = [
        f"Sir King — I assigned the specialists via Lead fan-out "
        f"(plan `{materialize.get('plan_id')}`).",
        "",
    ]
    if runs:
        lines.append("Queued for continuous dispatch:")
        for run in runs:
            role = str(run.get("owner_role") or "?").strip()
            run_id = str(run.get("run_id") or "").strip()
            task_id = str(run.get("task_id") or "").strip()
            lines.append(f"- {role}: run `{run_id}` · task `{task_id}`")
        lines.append("")
    if deferred:
        lines.append(f"Deferred (dependencies): {len(deferred)}")
        lines.append("")
    summary = str(receipt.get("summary") or "").strip()
    if summary:
        lines.append(summary)
    else:
        lines.append(
            f"Materialized {len(materialize.get('tasks') or [])} tasks; "
            f"queued {len(runs)} ready runs."
        )
    lines.append(
        "I did not write kickoff markdown — continuous worker owns the start. "
        f"— {lead_name}"
    )
    lines.append("")
    lines.append("Confidence: 8/10")
    return "\n".join(lines)


def _kick_continuous_dispatch() -> None:
    try:
        from app.workspace_agents.scheduler import kick_lead_fan_out_dispatch

        kick_lead_fan_out_dispatch(starts_bound=3)
    except Exception:
        pass


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


    threading.Thread(
        target=_kick_continuous_dispatch,
        daemon=True,
        name="lead-fan-out-dispatch-kick",
    ).start()

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
