"""Attach a specialist employee hint to a KAIRO IDE handoff action."""

from __future__ import annotations

import re
from typing import Any

from app.kairo.mission_spec import build_mission_spec
from app.workspace_agents.lead_fan_out import LeadFanOutError, materialize_lead_fan_out
from app.workspace_agents.lead_task_plan import detect_fan_out_intent
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

_MISSION_HEADER_RE = re.compile(
    r"(?im)^\s*(?:#{1,4}\s*)?mission(?:\s+(?:specification|id|title))?\s*(?::|$)",
)
_MISSION_FIELD_RE = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?:"
    r"objective|business context|success criteria|deliverables|constraints|"
    r"dependencies|recommended specialists|estimated complexity|"
    r"evidence required|definition of done"
    r")\s*:",
)
_IDENTITY_CHARTER_MARKERS = (
    re.compile(r"\byou are vaxon\b", re.IGNORECASE),
    re.compile(r"\bexecutive operating system\b", re.IGNORECASE),
    re.compile(r"\bchief of staff\b", re.IGNORECASE),
    re.compile(r"\bcore principles\b", re.IGNORECASE),
    re.compile(r"\bnon-negotiable rules\b", re.IGNORECASE),
    re.compile(r"\bautonomy levels\b", re.IGNORECASE),
    re.compile(r"\bfirst directive\b", re.IGNORECASE),
)


def is_identity_charter_text(task: str) -> bool:
    """Keep long identity/policy documents out of specialist task routing."""
    cleaned = str(task or "").strip()
    if len(cleaned) < 500:
        return False
    marker_count = sum(bool(pattern.search(cleaned)) for pattern in _IDENTITY_CHARTER_MARKERS)
    return marker_count >= 3


def is_mission_spec_text(task: str) -> bool:
    """Recognize explicit Mission Specs without introducing a mission object."""
    cleaned = str(task or "").strip()
    if not cleaned:
        return False
    if _MISSION_HEADER_RE.search(cleaned):
        return True
    return len(_MISSION_FIELD_RE.findall(cleaned)) >= 3


def _should_lead_decompose(task: str) -> bool:
    return (
        is_mission_spec_text(task)
        or detect_fan_out_intent(task)
        or bool(_LEAD_DECOMPOSE_HINT_RE.search(task))
    )


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
    action: dict[str, object] = {
        "type": "lead_fan_out",
        "target_workspace_id": target_workspace_id,
        "task": task,
        "plan_id": materialize.get("plan_id"),
        "mode": materialize.get("mode"),
        "tasks": materialize.get("tasks") or [],
        "runs": materialize.get("runs") or [],
        "deferred": materialize.get("deferred") or [],
        "receipt": materialize.get("receipt"),
        "plan": materialize.get("plan"),
    }
    action["mission_spec"] = build_mission_spec(
        task=task,
        workspace_id=target_workspace_id,
        action=action,
    )
    return action


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
    if is_identity_charter_text(task):
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
            use_model_tiebreak=True,
            dispatch_runtime=dispatch_model_tiebreak,
        )
    except Exception:
        return None
    if not decision.should_route or not decision.employee:
        return None
    action: dict[str, object] = {
        "type": "route_employee",
        "target_workspace_id": target_workspace_id,
        "task": task,
        "employee_id": decision.employee.employee_id,
        "employee_role": decision.employee.role,
        "employee_name": decision.employee.name,
        "routing_receipt": decision.routing_receipt,
        "model_receipt": decision.model_receipt,
    }
    action["mission_spec"] = build_mission_spec(
        task=task,
        workspace_id=target_workspace_id,
        action=action,
    )
    return action


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


__all__ = [
    "build_specialty_task_action",
    "enrich_handoff_with_teammate",
    "is_identity_charter_text",
    "is_mission_spec_text",
]
