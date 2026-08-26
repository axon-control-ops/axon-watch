"""Attach a specialist employee hint to a KAIRO IDE handoff action."""

from __future__ import annotations

import re
from typing import Any

from app.workspace_agents.lead_fan_out import LeadFanOutError, materialize_lead_fan_out
from app.workspace_agents.lead_task_plan import detect_fan_out_intent
from app.kairo.operator_input_safety import is_pasted_operational_context
from app.workspace_agents.teammate_route import (
    dispatch_model_tiebreak,
    route_teammate_decision,
)

# Actionable work verbs — include plural/past forms operators actually say.
_TASK_REQUEST_RE = re.compile(
    r"(?:^|\b)(?:please\s+)?(?:"
    r"fix(?:es|ed)?|implement(?:ed|ing)?|build(?:s|ing)?|investigate|"
    r"update(?:d|s)?|add(?:ed|ing)?|remove(?:d|s)?|refactor(?:ed|ing)?|"
    r"debug(?:ged|ging)?|resolve(?:d|s)?|create(?:d|s)?|change(?:d|s)?|"
    r"wire(?:d|s)?|repair(?:ed|s)?|push(?:ed|es|ing)?|ship(?:ped|ping)?|"
    r"deploy(?:ed|ing|s)?|publish(?:ed|ing)?|graduate|graduation|"
    r"help\s+me(?:\s+out)?"
    r")\b",
    re.IGNORECASE,
)

# Multi-stream operator asks should go through Lead decompose/fan-out, not a
# single specialist lease — e.g. canary + dashboard + graduation in one breath.
_LEAD_DECOMPOSE_HINT_RE = re.compile(
    r"\b(?:"
    r"help\s+me(?:\s+out)?|"
    r"graduation|graduate|"
    r"push(?:ed)?\s+(?:(?:the\s+)?(?:new\s+)?code\s+)?(?:to\s+)?canary|"
    r"ship(?:ped)?\s+to\s+canary|"
    r"ota\s+canary|"
    r"(?:dashboard|graduation|canary|ota).{0,100}(?:\band\b|,).{0,60}"
    r"(?:dashboard|graduation|canary|ota|fix(?:es)?)"
    r")\b",
    re.IGNORECASE,
)


def _should_lead_decompose(task: str) -> bool:
    return detect_fan_out_intent(task) or bool(_LEAD_DECOMPOSE_HINT_RE.search(task))


def _materialize_lead_action(
    task: str,
    *,
    target_workspace_id: str,
) -> dict[str, object] | None:
    try:
        materialize = materialize_lead_fan_out(
            workspace_id=target_workspace_id,
            goal=task,
            mode="auto",
            create_runs=True,
        )
    except (LeadFanOutError, Exception):
        return None
    return {
        "type": "lead_fan_out",
        "target_workspace_id": target_workspace_id,
        "task": task,
        "mode": materialize.get("mode"),
        "tasks": materialize.get("tasks") or [],
        "runs": materialize.get("runs") or [],
        "deferred": materialize.get("deferred") or [],
        "receipt": materialize.get("receipt"),
        "plan": materialize.get("plan"),
    }


def build_specialty_task_action(
    content: str,
    *,
    workspace_id: str | None,
) -> dict[str, object] | None:
    """Return a specialist dispatch action only for actionable, non-command turns."""
    task = str(content or "").strip()
    target_workspace_id = str(workspace_id or "").strip()
    if not task or not target_workspace_id:
        return None
    # Do not fan out a pasted Lead/run receipt merely because its historical
    # content mentions task verbs such as "push" or "Start".  A subsequent,
    # explicit operator instruction can still route work normally.
    if is_pasted_operational_context(task):
        return None
    # Public tunnel repair is a Connectors / Watch control — never a coding handoff.
    from app.kairo_tunnel_intents import detect_public_tunnel_repair_intent

    if detect_public_tunnel_repair_intent(task):
        return None
    if _should_lead_decompose(task):
        lead_action = _materialize_lead_action(
            task, target_workspace_id=target_workspace_id
        )
        if lead_action is not None:
            return lead_action
        # Fall through to single-route when materialize fails.
    if not _TASK_REQUEST_RE.search(task) and not _LEAD_DECOMPOSE_HINT_RE.search(task):
        return None
    try:
        decision = route_teammate_decision(
            workspace_id=target_workspace_id,
            prompt=task,
            use_model_tiebreak=False,
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
