"""HTTP routes for Gate 5 Lead planner fan-out."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.persistence import task_store
from app.workspace_agents import build_company_roster
from app.workspace_agents.lead_fan_out import LeadFanOutError, materialize_lead_fan_out
from app.workspace_agents.lead_replan import (
    LeadReplanError,
    replan_lead_goal,
    synthesize_lead_plan,
)
from app.workspace_agents.lead_task_persist import persist_lead_task_plan
from app.workspace_agents.lead_task_plan import LeadPlanRosterMember, build_lead_task_plan

router = APIRouter(tags=["lead-planner"])


class LeadPlanRequest(BaseModel):
    goal: str = Field(min_length=1)
    mode: Literal["auto", "fan_out", "sequential"] = "auto"
    persist: bool = False
    attachment_ids: list[str] = Field(default_factory=list)
    source_message_id: str | None = None


class LeadFanOutRequest(BaseModel):
    goal: str = Field(min_length=1)
    mode: Literal["auto", "fan_out", "sequential"] = "auto"
    create_runs: bool = True
    attachment_ids: list[str] = Field(default_factory=list)
    source_message_id: str | None = None
    dispatch_workers: bool = False
    confirmed: bool = False


class LeadReplanRequest(BaseModel):
    goal: str = Field(min_length=1)
    mode: Literal["auto", "fan_out", "sequential"] = "auto"
    create_runs: bool = True
    attachment_ids: list[str] = Field(default_factory=list)
    source_message_id: str | None = None
    dispatch_workers: bool = False
    confirmed: bool = False


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


@router.post("/api/workspaces/{workspace_id}/lead/plan")
def workspace_lead_plan(workspace_id: str, body: LeadPlanRequest) -> dict[str, Any]:
    goal = body.goal.strip()
    if not goal:
        raise HTTPException(status_code=400, detail="goal must not be empty")
    try:
        plan = build_lead_task_plan(
            goal=goal,
            roster=_roster_members(workspace_id),
            mode=body.mode,  # type: ignore[arg-type]
            attachment_ids=body.attachment_ids,
            source_message_id=body.source_message_id,
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
    if body.dispatch_workers and not body.confirmed:
        raise HTTPException(
            status_code=400,
            detail="dispatch_workers requires confirmed=true (operator approval)",
        )
    try:
        return materialize_lead_fan_out(
            workspace_id=workspace_id,
            goal=body.goal,
            mode=body.mode,  # type: ignore[arg-type]
            create_runs=body.create_runs,
            attachment_ids=body.attachment_ids,
            source_message_id=body.source_message_id,
            dispatch_workers=body.dispatch_workers,
        )
    except LeadFanOutError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except task_store.TaskLedgerError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/api/workspaces/{workspace_id}/lead/replan")
def workspace_lead_replan(workspace_id: str, body: LeadReplanRequest) -> dict[str, Any]:
    if body.dispatch_workers and not body.confirmed:
        raise HTTPException(
            status_code=400,
            detail="dispatch_workers requires confirmed=true (operator approval)",
        )
    try:
        return replan_lead_goal(
            workspace_id=workspace_id,
            goal=body.goal,
            mode=body.mode,  # type: ignore[arg-type]
            create_runs=body.create_runs,
            attachment_ids=body.attachment_ids,
            source_message_id=body.source_message_id,
            dispatch_workers=body.dispatch_workers,
        )
    except LeadReplanError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except task_store.TaskLedgerError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/api/lead/plans/{plan_id}/synthesize")
def lead_plan_synthesize(plan_id: str) -> dict[str, Any]:
    try:
        return synthesize_lead_plan(plan_id)
    except LeadReplanError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
