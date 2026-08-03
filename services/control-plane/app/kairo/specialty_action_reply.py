"""Evidence-state reply copy for VAXON specialty actions."""

from __future__ import annotations

from app.kairo.mission_spec import format_mission_spec


def build_specialty_action_reply(action: dict[str, object]) -> tuple[str, str]:
    action_type = str(action.get("type") or "")
    mission_spec = action.get("mission_spec")
    if action_type == "lead_fan_out":
        mode = str(action.get("mode") or "decompose").strip() or "decompose"
        task_count = len(action.get("tasks") or [])
        dispatch_line = (
            f"Lead materialized {mode}"
            + (f" across {task_count} task(s)" if task_count else "")
            + "; the Task Board is opening."
        )
        reply = (
            f"{format_mission_spec(mission_spec, evidence_state='Dispatched')}\n\n"
            f"**Dispatch evidence:** {dispatch_line}"
            if isinstance(mission_spec, dict)
            else f"Dispatched: {dispatch_line}"
        )
        return reply, f"Dispatched: {dispatch_line}"

    employee_name = str(action.get("employee_name") or "the specialist")
    employee_role = str(action.get("employee_role") or "specialist")
    planned_line = (
        f"Routing is prepared for {employee_name}, the {employee_role} specialist."
    )
    reply = (
        f"{format_mission_spec(mission_spec, evidence_state='Planned')}\n\n"
        f"**Next state:** {planned_line}"
        if isinstance(mission_spec, dict)
        else f"Planned: {planned_line}"
    )
    return reply, f"Planned: {planned_line}"


__all__ = ["build_specialty_action_reply"]
