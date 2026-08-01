"""Operator autonomy + Mission Control CEO routes (attend, decisions, Lead engage)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["operator-autonomy"])


@router.get("/api/operator/mission-control/critical-work")
def operator_mission_control_critical_work(
    focused_workspace_id: str = "",
) -> dict[str, object]:
    """VAXON Mission Control CEO — ask Leads and rank critical fleet work."""
    from app.operator_mission_control_ceo import build_mission_control_critical_work

    return build_mission_control_critical_work(
        focused_workspace_id=focused_workspace_id.strip() or None,
    )


@router.post("/api/operator/mission-control/engage-leads")
def operator_mission_control_engage_leads(
    max_plans: int = 5,
) -> dict[str, object]:
    """VAXON CEO — clear awaiting Lead reviews under Full autonomy."""
    from app.operator_mission_control_ceo import engage_awaiting_lead_plans

    result = engage_awaiting_lead_plans(
        max_plans=max_plans,
        require_full_autonomy=True,
    )
    if not result.get("ok") and result.get("reason") == "autonomy_not_full":
        raise HTTPException(
            status_code=400,
            detail="engage-leads requires autonomy_mode=full",
        )
    return result


@router.get("/api/operator/autonomy/status")
def operator_autonomy_status(workspace_id: str = "") -> dict[str, object]:
    """Read-only Mission Control autonomy feed (mode, scheduler, receipts)."""
    from app.workspace_agents.autonomous_attention import build_autonomy_status_feed

    return build_autonomy_status_feed(workspace_id=workspace_id.strip() or None)


@router.post("/api/operator/autonomy/scan")
def operator_autonomy_scan() -> dict[str, object]:
    """Operator-triggered attend scan (also runs on Full-autonomy scheduler ticks)."""
    from app.persistence import operator_presence_settings_store
    from app.workspace_agents.autonomous_attention import run_autonomous_attention_scan

    settings = operator_presence_settings_store.load_settings()
    mode = str(settings.get("autonomy_mode") or "manual").strip().lower()
    if mode != "full":
        raise HTTPException(
            status_code=400,
            detail=f"attend scan requires autonomy_mode=full (current={mode})",
        )
    return run_autonomous_attention_scan(include_lead_checkin=False)


@router.post("/api/operator/autonomy/decisions/{receipt_id}")
def operator_autonomy_decision_resolve(
    receipt_id: str,
    body: dict[str, object],
) -> dict[str, object]:
    """Resolve one exact critical/dangerous decision as approve or reject."""
    from app.workspace_agents.autonomous_attention import resolve_autonomy_decision

    resolution = str(body.get("resolution") or "").strip().lower()
    try:
        return resolve_autonomy_decision(receipt_id, resolution=resolution)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
