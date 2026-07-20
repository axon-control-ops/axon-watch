"""Fleet control routes for continuous-worker scheduler."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.workspace_agents import WorkspaceAgentError, get_company_roster
from app.workspace_agents.fleet_control import (
    build_scheduler_status,
    patch_scheduler_settings,
    set_employee_enabled,
    stop_active_runs,
)

router = APIRouter(tags=["worker-scheduler"])


class WorkerSchedulerPatchRequest(BaseModel):
    scheduler_enabled: bool | None = None
    max_active: int | None = Field(default=None, ge=1, le=16)
    max_starts_per_tick: int | None = Field(default=None, ge=1, le=8)


class EmployeeEnabledPatchRequest(BaseModel):
    enabled: bool


@router.get("/api/worker-scheduler")
def worker_scheduler_get() -> dict[str, Any]:
    return build_scheduler_status()


@router.patch("/api/worker-scheduler")
def worker_scheduler_patch(body: WorkerSchedulerPatchRequest) -> dict[str, Any]:
    patch = body.model_dump(exclude_none=True)
    if not patch:
        raise HTTPException(status_code=400, detail="no worker scheduler fields to patch")
    return patch_scheduler_settings(patch)


@router.post("/api/worker-scheduler/stop-active")
def worker_scheduler_stop_active() -> dict[str, Any]:
    return stop_active_runs()


@router.patch("/api/workspaces/{workspace_id}/company/employees/{employee_id}")
def workspace_employee_patch(
    workspace_id: str,
    employee_id: str,
    body: EmployeeEnabledPatchRequest,
) -> dict[str, Any]:
    try:
        roster = get_company_roster(workspace_id)
    except WorkspaceAgentError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    company = roster.get("company") if isinstance(roster, dict) else None
    employees = []
    if isinstance(company, dict):
        raw_employees = company.get("employees")
        if isinstance(raw_employees, list):
            employees = raw_employees

    target_id = employee_id.strip()
    match: dict[str, Any] | None = None
    for row in employees:
        if not isinstance(row, dict):
            continue
        if str(row.get("employee_id") or "").strip() == target_id:
            match = row
            break
    if match is None:
        raise HTTPException(status_code=404, detail=f"employee not found: {target_id}")

    role = str(match.get("role") or "").strip()
    if not role:
        raise HTTPException(status_code=400, detail="employee role missing")

    updated = set_employee_enabled(
        workspace_id=workspace_id,
        role=role,
        enabled=body.enabled,
    )
    # Return refreshed company snapshot so the UI can update without a second fetch.
    refreshed = get_company_roster(workspace_id)
    return {
        **updated,
        **refreshed,
    }
