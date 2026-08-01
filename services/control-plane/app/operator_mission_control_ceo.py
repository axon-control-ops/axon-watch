"""VAXON Mission Control CEO — ask Leads, rank critical fleet work, engage reviews."""

from __future__ import annotations

import logging
from typing import Any

from app.operator_fleet_advice import workspace_advice_label

logger = logging.getLogger(__name__)

DEFAULT_ENGAGE_MAX = 5


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

    from app.persistence import operator_presence_settings_store

    mode = str(
        operator_presence_settings_store.load_settings().get("autonomy_mode") or ""
    ).strip().lower()
    auto_on = mode == "full"

    from app.mission_control_plate import advise_from_plate, collect_mission_control_plate

    plate = collect_mission_control_plate(focused_workspace_id=focused)

    advise = ""
    advise_ui_action: dict[str, Any] | None = None
    if winner:
        lead = str(winner.get("lead_name") or "Lead")
        name = str(winner.get("display_name") or "that company")
        title = str(winner.get("title") or "Lead-team plan")
        cross = bool(focused and winner.get("workspace_id") != focused)
        if auto_on:
            advise = (
                f"I am clearing Lead reviews — next up {lead}"
                + (f" ({name})" if cross else "")
                + f": “{title}”."
            )
        elif cross:
            advise = (
                f"{lead} ({name}) has a Lead-team plan waiting — "
                f"engage “{title}” before more work here."
            )
        else:
            advise = f"{lead} has a Lead-team plan waiting — engage “{title}”."
        advise_ui_action = {
            "type": "engage_lead_plans" if auto_on else "switch_workspace",
            "workspace_id": winner.get("workspace_id"),
            "focus_attention": True,
            "plan_id": winner.get("plan_id"),
        }
    else:
        # Lead plans clear ≠ Mission Control clear — surface Waiting / failures.
        advise, advise_ui_action = advise_from_plate(plate, auto_on=auto_on)

    return {
        "ok": True,
        "generated_at": utc_now_iso(),
        "focused_workspace_id": focused,
        "autonomy_full": auto_on,
        "leads_asked": len(leads),
        "awaiting_plan_count": len(plans),
        "leads": leads,
        "winner": winner,
        "plate": plate,
        "advise": advise,
        "advise_ui_action": advise_ui_action,
    }


def engage_awaiting_lead_plans(
    *,
    max_plans: int = DEFAULT_ENGAGE_MAX,
    require_full_autonomy: bool = True,
) -> dict[str, Any]:
    """VAXON CEO: acknowledge finished Lead syntheses so the plate does not stall.

    Under Full autonomy, awaiting_engagement means Lead already rolled up — VAXON
    owns the review close-out (not another operator chore). Caps per tick.
    """
    from app.host_context.models import utc_now_iso
    from app.persistence import operator_presence_settings_store
    from app.workspace_agents import lead_plan_store
    from app.workspace_agents.lead_vaxon_handoff import list_awaiting_engagement_plans

    settings = operator_presence_settings_store.load_settings()
    mode = str(settings.get("autonomy_mode") or "").strip().lower()
    autonomy_full = mode == "full"
    if require_full_autonomy and not autonomy_full:
        return {
            "ok": False,
            "reason": "autonomy_not_full",
            "autonomy_full": False,
            "engaged": [],
            "remaining": 0,
            "generated_at": utc_now_iso(),
        }

    plans = list_awaiting_engagement_plans(workspace_id=None)
    # One plan per workspace per tick — clear the fleet fairly, newest first.
    seen_ws: set[str] = set()
    engaged: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    bound = max(1, min(20, int(max_plans)))
    for plan in plans:
        if len(engaged) >= bound:
            break
        plan_id = str(plan.get("plan_id") or "").strip()
        workspace_id = str(plan.get("workspace_id") or "").strip()
        if not plan_id or not workspace_id or workspace_id in seen_ws:
            continue
        seen_ws.add(workspace_id)
        try:
            updated = lead_plan_store.set_plan_status(plan_id, "completed")
            lead_plan_store.append_receipt(
                plan_id=plan_id,
                workspace_id=workspace_id,
                kind="vaxon_ceo_engaged",
                payload={"reason": "full_autonomy_lead_review_closeout"},
            )
            engaged.append(
                {
                    "plan_id": plan_id,
                    "workspace_id": workspace_id,
                    "goal": _plan_goal(plan),
                    "status": str(updated.get("status") or "completed"),
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("CEO engage failed plan=%s: %s", plan_id, exc)
            errors.append({"plan_id": plan_id, "reason": str(exc)})

    remaining = max(0, len(plans) - len(engaged))
    # #region agent log
    try:
        import json
        import time

        with open(
            "/home/edp/axon-nvme/repos/axon-watch/.cursor/debug-db8bb4.log",
            "a",
            encoding="utf-8",
        ) as _dbg:
            _dbg.write(
                json.dumps(
                    {
                        "sessionId": "db8bb4",
                        "runId": "ceo-engage",
                        "hypothesisId": "C1",
                        "location": "operator_mission_control_ceo.py:engage_awaiting_lead_plans",
                        "message": "ceo engaged lead plans",
                        "data": {
                            "autonomy_full": autonomy_full,
                            "awaiting_before": len(plans),
                            "engaged": len(engaged),
                            "remaining": remaining,
                            "workspaces": [row.get("workspace_id") for row in engaged],
                        },
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion
    return {
        "ok": True,
        "autonomy_full": autonomy_full,
        "engaged": engaged,
        "errors": errors,
        "remaining": remaining,
        "spoken": (
            f"Cleared {len(engaged)} Lead review"
            f"{'' if len(engaged) == 1 else 's'}"
            + (f"; {remaining} still queued." if remaining else ".")
            if engaged
            else "No Lead reviews waiting."
        ),
        "generated_at": utc_now_iso(),
    }


def run_ceo_attend_hooks() -> dict[str, Any]:
    """Machine CEO + Lead-review engagement for one attend-scan tick."""
    out: dict[str, Any] = {}
    try:
        from app.host_context.machine_ceo import run_machine_ceo_tick

        out["machine_ceo"] = run_machine_ceo_tick(auto_kill=True)
    except Exception:  # noqa: BLE001
        logger.exception("machine ceo tick during attend scan failed")
        out["machine_ceo"] = {"error": "machine_ceo_failed"}
    try:
        eng = engage_awaiting_lead_plans(max_plans=5, require_full_autonomy=True)
        out["lead_engagement"] = eng
        # #region agent log
        try:
            import json
            import time

            with open(
                "/home/edp/axon-nvme/repos/axon-watch/.cursor/debug-db8bb4.log",
                "a",
                encoding="utf-8",
            ) as _dbg:
                _dbg.write(
                    json.dumps(
                        {
                            "sessionId": "db8bb4",
                            "runId": "ceo-engage",
                            "hypothesisId": "C1",
                            "location": "operator_mission_control_ceo.py:run_ceo_attend_hooks",
                            "message": "attend scan lead_engagement",
                            "data": {
                                "ok": eng.get("ok"),
                                "engaged": len(eng.get("engaged") or []),
                                "remaining": eng.get("remaining"),
                                "reason": eng.get("reason"),
                            },
                            "timestamp": int(time.time() * 1000),
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion
    except Exception:  # noqa: BLE001
        logger.exception("lead engagement during attend scan failed")
        out["lead_engagement"] = {"error": "lead_engagement_failed"}
    try:
        from app.workspace_agents.ceo_pending_approve import ceo_auto_approve_pending

        out["pending_approvals"] = ceo_auto_approve_pending(
            max_decisions=5,
            require_full_autonomy=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception("CEO pending approve during attend scan failed")
        out["pending_approvals"] = {"error": "ceo_pending_approve_failed"}
    return out


__all__ = [
    "build_mission_control_critical_work",
    "collect_awaiting_lead_plan_facts",
    "engage_awaiting_lead_plans",
    "run_ceo_attend_hooks",
]
