"""HTTP routes for Gate 5 Lead planner fan-out."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.persistence import task_store
from app.workspace_agents import build_company_roster
from app.workspace_agents import lead_plan_store
from app.workspace_agents.lead_fan_out import LeadFanOutError, materialize_lead_fan_out
from app.workspace_agents.lead_plan_model import resolve_lead_task_plan
from app.workspace_agents.lead_replan import (
    LeadReplanError,
    replan_lead_goal,
    synthesize_lead_plan,
)
from app.workspace_agents.lead_task_persist import persist_lead_task_plan
from app.workspace_agents.lead_task_plan import LeadPlanRosterMember

router = APIRouter(tags=["lead-planner"])

_PLAN_MODE = Literal["auto", "fan_out", "sequential", "decompose"]


class LeadPlanRequest(BaseModel):
    goal: str = Field(min_length=1)
    mode: _PLAN_MODE = "auto"
    persist: bool = False
    use_model: bool = True


class LeadFanOutRequest(BaseModel):
    goal: str = Field(min_length=1)
    mode: _PLAN_MODE = "auto"
    create_runs: bool = True
    use_model: bool = True


class LeadReplanRequest(BaseModel):
    goal: str = Field(min_length=1)
    mode: _PLAN_MODE = "auto"
    create_runs: bool = True


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


@router.get("/api/workspaces/{workspace_id}/lead/plans")
def workspace_lead_plans(workspace_id: str, limit: int = 50) -> dict[str, Any]:
    cleaned = str(workspace_id or "").strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="workspace_id is required")
    items = lead_plan_store.list_workspace_plans(cleaned, limit=limit)
    return {"workspace_id": cleaned, "items": items, "count": len(items)}


def _vaxon_handoff_for_plan(plan_id: str) -> dict[str, str] | None:
    """Where "Review now" should navigate: the VAXON chat message that carries
    this plan's rollup, if Lead has posted one yet (see lead_vaxon_handoff.py's
    HANDOFF_RECEIPT_KIND = "lead_synthesis_vaxon_posted")."""
    for receipt in reversed(lead_plan_store.list_receipts(plan_id)):
        if str(receipt.get("kind") or "") != "lead_synthesis_vaxon_posted":
            continue
        payload = receipt.get("payload")
        if not isinstance(payload, dict):
            continue
        thread_id = str(payload.get("thread_id") or "").strip()
        message_id = str(payload.get("message_id") or "").strip()
        if thread_id:
            return {"thread_id": thread_id, "message_id": message_id}
    return None


@router.get("/api/lead/plans/{plan_id}")
def lead_plan_get(plan_id: str) -> dict[str, Any]:
    cleaned = str(plan_id or "").strip()
    plan = lead_plan_store.get_plan(cleaned)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"lead plan not found: {cleaned}")
    task_links = lead_plan_store.plan_task_links(cleaned)
    return {
        **plan,
        "task_links": task_links,
        "task_ids": [link["task_id"] for link in task_links],
        "awaiting_engagement": str(plan.get("status") or "") == "awaiting_engagement",
        "vaxon_handoff": _vaxon_handoff_for_plan(cleaned),
    }


@router.post("/api/workspaces/{workspace_id}/lead/plan")
def workspace_lead_plan(workspace_id: str, body: LeadPlanRequest) -> dict[str, Any]:
    goal = body.goal.strip()
    if not goal:
        raise HTTPException(status_code=400, detail="goal must not be empty")
    try:
        plan = resolve_lead_task_plan(
            goal=goal,
            roster=_roster_members(workspace_id),
            mode=body.mode,
            workspace_id=workspace_id,
            use_model=body.use_model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not body.persist:
        return {"workspace_id": workspace_id, "plan": plan.to_dict(), "persisted": False}
    try:
        persisted = persist_lead_task_plan(workspace_id=workspace_id, plan=plan)
    except task_store.TaskLedgerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {**persisted, "persisted": True}


@router.post("/api/workspaces/{workspace_id}/lead/fan-out")
def workspace_lead_fan_out(workspace_id: str, body: LeadFanOutRequest) -> dict[str, Any]:
    try:
        return materialize_lead_fan_out(
            workspace_id=workspace_id,
            goal=body.goal,
            mode=body.mode,  # type: ignore[arg-type]
            create_runs=body.create_runs,
            use_model=body.use_model,
        )
    except LeadFanOutError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except task_store.TaskLedgerError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/api/workspaces/{workspace_id}/lead/replan")
def workspace_lead_replan(workspace_id: str, body: LeadReplanRequest) -> dict[str, Any]:
    try:
        return replan_lead_goal(
            workspace_id=workspace_id,
            goal=body.goal,
            mode=body.mode,  # type: ignore[arg-type]
            create_runs=body.create_runs,
        )
    except LeadReplanError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except task_store.TaskLedgerError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


class LeadPlanStatusRequest(BaseModel):
    status: Literal["completed", "cancelled", "awaiting_engagement"] = "completed"


@router.post("/api/lead/plans/{plan_id}/status")
def lead_plan_set_status(plan_id: str, body: LeadPlanStatusRequest) -> dict[str, Any]:
    cleaned = str(plan_id or "").strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="plan_id is required")
    plan = lead_plan_store.get_plan(cleaned)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"lead plan not found: {cleaned}")
    try:
        updated = lead_plan_store.set_plan_status(cleaned, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    task_links = lead_plan_store.plan_task_links(cleaned)
    return {
        **updated,
        "task_links": task_links,
        "task_ids": [link["task_id"] for link in task_links],
        "awaiting_engagement": str(updated.get("status") or "") == "awaiting_engagement",
    }


@router.post("/api/lead/plans/{plan_id}/synthesize")
def lead_plan_synthesize(plan_id: str) -> dict[str, Any]:
    try:
        return synthesize_lead_plan(plan_id)
    except LeadReplanError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
