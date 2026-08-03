"""VAXON Lead charter intents — persist Lead plans via the lead-planner path."""

from __future__ import annotations

import re
from typing import Any

from app.kairo_participant_memory import apply_participant_address
from app.kairo_workspace_intents import infer_workspace_id_from_content
from app.kairo.operator_input_safety import is_pasted_operational_context
from app.kairo_workspace_register_intents import (
    _SCHOOL_WORKSPACE_ID,
    resolve_known_purpose_workspace_id,
)
from app.persistence import task_store
from app.workspace_agents import build_company_roster
from app.workspace_agents.lead_task_persist import persist_lead_task_plan
from app.workspace_agents.lead_task_plan import LeadPlanRosterMember, build_lead_task_plan

_CHARTER_RE = re.compile(
    r"\b(?:charter|commission|task|assign)\b.{0,80}\b(?:lindi|lead|dana)\b"
    r"|\b(?:persist|save|create)\b.{0,40}\blead\s+plan\b"
    r"|\blead\s+plan\b.{0,40}\b(?:persist|save|create)\b"
    r"|\bstand\s+up\b.{0,80}\b(?:aftercare|edp\s+excellence|sibling\s+app)\b",
    re.IGNORECASE | re.DOTALL,
)


def is_lead_charter_utterance(content: str) -> bool:
    trimmed = content.strip()
    return bool(
        trimmed
        and not is_pasted_operational_context(trimmed)
        and _CHARTER_RE.search(trimmed)
    )


def resolve_lead_charter_workspace_id(
    content: str,
    *,
    workspace_id: str | None,
) -> str:
    inferred = infer_workspace_id_from_content(content)
    if inferred:
        return inferred
    purpose = resolve_known_purpose_workspace_id(content)
    if purpose:
        return purpose
    current = (workspace_id or "").strip()
    if current.startswith("workspace_"):
        return current
    lower = content.lower()
    if any(
        token in lower
        for token in ("lindi", "edp excellence", "aftercare", "school of excellence", "sibling app")
    ):
        return _SCHOOL_WORKSPACE_ID
    return _SCHOOL_WORKSPACE_ID


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


def persist_charter_lead_plan(
    *,
    goal: str,
    workspace_id: str,
    mode: str = "fan_out",
) -> dict[str, Any]:
    cleaned = goal.strip()
    if not cleaned:
        raise ValueError("goal must not be empty")
    roster = _roster_members(workspace_id)
    if not roster:
        raise ValueError(f"no company roster for {workspace_id}")
    # Charters are company-wide: fan out to specialists; Lindi synthesizes.
    plan = build_lead_task_plan(goal=cleaned, roster=roster, mode=mode)  # type: ignore[arg-type]
    return persist_lead_task_plan(workspace_id=workspace_id, plan=plan)


def maybe_handle_lead_charter_intent(
    *,
    content: str,
    workspace_id: str | None,
    guest_name: str | None,
) -> dict[str, Any] | None:
    trimmed = content.strip()
    if not trimmed or not is_lead_charter_utterance(trimmed):
        return None

    target_id = resolve_lead_charter_workspace_id(trimmed, workspace_id=workspace_id)
    try:
        persisted = persist_charter_lead_plan(goal=trimmed, workspace_id=target_id)
    except (ValueError, task_store.TaskLedgerError) as exc:
        return {
            "turn_kind": "action",
            "reply": apply_participant_address(
                f"I couldn't persist the Lead plan for `{target_id}`: {exc}",
                guest_name,
            ),
            "source": "template",
            "command_content": None,
            "action": None,
            "artifacts": [],
            "action_tier": "reversible_auto",
        }

    plan_id = str(persisted.get("plan_id") or "")
    plan = persisted.get("plan") if isinstance(persisted.get("plan"), dict) else {}
    items = plan.get("items") if isinstance(plan.get("items"), list) else []
    task_count = len(items)
    roles = sorted(
        {
            str(item.get("owner_role") or "").strip()
            for item in items
            if isinstance(item, dict) and str(item.get("owner_role") or "").strip()
        }
    )
    role_bit = ", ".join(roles) if roles else "specialists"
    return {
        "turn_kind": "action",
        "reply": apply_participant_address(
            f"Lead plan persisted for **EDP Excellence** (`{target_id}`): "
            f"`{plan_id}` with {task_count} task(s) for {role_bit}. "
            "Lindi owns the rollup — I'll brief you at Decide gates.",
            guest_name,
        ),
        "source": "template",
        "command_content": None,
        "action": {"type": "switch_workspace", "workspace_id": target_id},
        "artifacts": [
            {
                "artifact_id": f"lead-plan:{plan_id}",
                "title": "Lead plan persisted",
                "summary": f"{task_count} tasks for {target_id}",
                "body": (
                    f"plan_id={plan_id}\n"
                    f"workspace_id={target_id}\n"
                    f"mode={plan.get('mode')}\n"
                    f"goal={plan.get('goal')}"
                ),
                "sources": [{"label": "lead-planner", "detail": "persist_lead_task_plan"}],
                "actions": [
                    {
                        "label": "Open EDP Excellence",
                        "ui_action": {
                            "type": "switch_workspace",
                            "workspace_id": target_id,
                        },
                    }
                ],
            }
        ],
        "action_tier": "reversible_auto",
    }
