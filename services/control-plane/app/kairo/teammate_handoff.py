"""Attach a specialist employee hint to a KAIRO IDE handoff action."""

from __future__ import annotations

import re
from typing import Any

from app.workspace_agents.teammate_route import (
    dispatch_model_tiebreak,
    route_teammate_decision,
)

_TASK_REQUEST_RE = re.compile(
    r"(?:^|\b)(?:please\s+)?(?:fix|implement|build|investigate|update|add|remove|"
    r"refactor|debug|resolve|create|change|wire|repair)\b",
    re.IGNORECASE,
)


def build_specialty_task_action(
    content: str,
    *,
    workspace_id: str | None,
) -> dict[str, object] | None:
    """Return a specialist dispatch action only for actionable, non-command turns."""
    task = str(content or "").strip()
    target_workspace_id = str(workspace_id or "").strip()
    if not task or not target_workspace_id or not _TASK_REQUEST_RE.search(task):
        return None
    try:
        decision = route_teammate_decision(
            workspace_id=target_workspace_id,
            prompt=task,
            use_model_tiebreak=True,
            dispatch_runtime=dispatch_model_tiebreak,
        )
    except Exception:
        return None
    if not decision.should_route or not decision.employee:
        return None
    return {
        "type": "route_employee",
        "target_workspace_id": target_workspace_id,
        "task": task,
        "employee_id": decision.employee.employee_id,
        "employee_role": decision.employee.role,
        "employee_name": decision.employee.name,
        "routing_receipt": decision.routing_receipt,
        "model_receipt": decision.model_receipt,
    }


def enrich_handoff_with_teammate(
    action: dict[str, object],
    *,
    resolved_workspace_id: str | None,
    fallback_prompt: str,
) -> dict[str, object]:
    target_workspace_id = str(
        action.get("target_workspace_id") or resolved_workspace_id or ""
    ).strip()
    task = str(action.get("task") or fallback_prompt).strip()
    if not target_workspace_id or not task:
        return action
    try:
        decision = route_teammate_decision(
            workspace_id=target_workspace_id,
            prompt=task,
            use_model_tiebreak=True,
            dispatch_runtime=dispatch_model_tiebreak,
        )
    except Exception:
        return action
    if not decision.should_route or not decision.employee:
        return action
    return {
        **action,
        "employee_id": decision.employee.employee_id,
        "employee_role": decision.employee.role,
        "employee_name": decision.employee.name,
        "routing_receipt": decision.routing_receipt,
        "model_receipt": decision.model_receipt,
    }


__all__ = ["build_specialty_task_action", "enrich_handoff_with_teammate"]
