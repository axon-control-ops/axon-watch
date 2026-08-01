"""VAXON Mission Control CEO — ask Leads, rank critical fleet work, engage reviews."""

from __future__ import annotations

import logging
from typing import Any

from app.operator_fleet_advice import workspace_advice_label

logger = logging.getLogger(__name__)

DEFAULT_ENGAGE_BATCH = 5


def _plan_goal(plan: dict[str, Any]) -> str:
    goal = str(plan.get("goal") or plan.get("title") or plan.get("summary") or "").strip()
    if not goal:
        return "Lead-team plan"
    return goal if len(goal) <= 96 else f"{goal[:95].rstrip()}…"


def _lead_name_for(
    workspace_id: str,
    lead_rows: list[dict[str, Any]],
) -> str:
    for row in lead_rows:
        if str(row.get("workspace_id") or "") == workspace_id:
            return str(row.get("lead_name") or "Lead").strip() or "Lead"
    return "Lead"


def collect_awaiting_lead_plan_facts(
    *,
    display_names: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """One fact per workspace with an awaiting-engagement Lead plan (newest first)."""
    from app.workspace_agents.fleet_leads_context import collect_fleet_lead_rows
    from app.workspace_agents.lead_vaxon_handoff import list_awaiting_engagement_plans

    lead_rows = collect_fleet_lead_rows()
    plans = list_awaiting_engagement_plans(workspace_id=None)
    seen: set[str] = set()
    facts: list[dict[str, Any]] = []
    for plan in plans:
        workspace_id = str(plan.get("workspace_id") or "").strip()
        if not workspace_id or workspace_id in seen:
            continue
        seen.add(workspace_id)
        facts.append(
            {
                "kind": "awaiting_lead_plan",
                "rank": 3,
                "workspace_id": workspace_id,
                "display_name": workspace_advice_label(workspace_id, display_names),
                "lead_name": _lead_name_for(workspace_id, lead_rows),
                "plan_id": str(plan.get("plan_id") or "") or None,
                "run_id": None,
                "signal_id": None,
                "title": _plan_goal(plan),
            }
        )
    return facts


def build_mission_control_critical_work(
    *,
    focused_workspace_id: str | None = None,
    display_names: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Ask Leads (ledger plate) and rank the single critical Mission Control move."""
    from app.host_context.models import utc_now_iso
    from app.workspace_agents.fleet_leads_context import collect_fleet_lead_rows
    from app.workspace_agents.lead_vaxon_handoff import list_awaiting_engagement_plans

    focused = str(focused_workspace_id or "").strip() or None
    lead_rows = collect_fleet_lead_rows()
    plans = list_awaiting_engagement_plans(workspace_id=None)
    plans_by_ws: dict[str, list[dict[str, Any]]] = {}
    for plan in plans:
        wid = str(plan.get("workspace_id") or "").strip()
        if not wid:
            continue
        plans_by_ws.setdefault(wid, []).append(plan)

    leads: list[dict[str, Any]] = []
    for row in lead_rows:
        wid = str(row.get("workspace_id") or "").strip()
        awaiting = plans_by_ws.get(wid) or []
        leads.append(
            {
                "workspace_id": wid,
                "lead_name": str(row.get("lead_name") or "Lead"),
                "display_name": workspace_advice_label(wid, display_names)
                or str(row.get("display_name") or wid),
                "owns": str(row.get("owns") or ""),
                "awaiting_engagement_count": len(awaiting),
                "awaiting_engagement_plans": [
                    {
                        "plan_id": str(item.get("plan_id") or ""),
                        "goal": _plan_goal(item),
                    }
                    for item in awaiting[:3]
                ],
            }
        )

    facts = collect_awaiting_lead_plan_facts(display_names=display_names)
    winner = None
    if facts:
        # Prefer focused workspace plate when it has an awaiting plan; else fleet-first.
        if focused:
            winner = next(
                (item for item in facts if item.get("workspace_id") == focused),
                None,
            )
        if winner is None:
            winner = facts[0]

    advise = ""
    if winner:
        lead = str(winner.get("lead_name") or "Lead")
        name = str(winner.get("display_name") or "that company")
        title = str(winner.get("title") or "Lead-team plan")
        cross = bool(focused and winner.get("workspace_id") != focused)
        if cross:
            advise = (
                f"{lead} ({name}) has a Lead-team plan waiting — "
                f"engage “{title}” before more work here."
            )
        else:
            advise = (
                f"{lead} has a Lead-team plan waiting — engage “{title}”."
            )

    return {
        "ok": True,
        "generated_at": utc_now_iso(),
        "focused_workspace_id": focused,
        "leads_asked": len(leads),
        "awaiting_plan_count": len(plans),
        "leads": leads,
        "winner": winner,
        "advise": advise,
        "advise_ui_action": (
            {
                "type": "switch_workspace",
                "workspace_id": winner.get("workspace_id"),
                "focus_attention": True,
                "plan_id": winner.get("plan_id"),
            }
            if winner
            else None
        ),
    }


__all__ = [
    "build_mission_control_critical_work",
    "collect_awaiting_lead_plan_facts",
]
