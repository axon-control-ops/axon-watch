"""HTTP API for durable cross-workspace missions."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.workspace_missions import (
    cancel_mission,
    create_workspace_mission,
    get_workspace_mission,
    list_workspace_missions,
    preview_workspace_impact,
    promote_mission,
    retry_mission,
    verify_mission,
)

router = APIRouter(tags=["workspace-missions"])


class MissionImpactPreviewRequest(BaseModel):
    source_workspace_id: str = Field(min_length=1)
    goal: str = ""
    changed_paths: list[str] = Field(default_factory=list)


class MissionCreateRequest(BaseModel):
    source_workspace_id: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    risk: str = "normal"
    source_task_id: str | None = None
    source_run_id: str | None = None
    changed_paths: list[str] = Field(default_factory=list)


def _invoke(action):
    try:
        return action()
    except ValueError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 409 if "not ready" in detail else 400
        raise HTTPException(status_code=status, detail=detail) from exc


@router.post("/api/workspace-missions/impact-preview")
def mission_impact_preview(body: MissionImpactPreviewRequest) -> dict[str, Any]:
    return preview_workspace_impact(
        body.source_workspace_id, body.goal, body.changed_paths
    )


@router.post("/api/workspace-missions")
def mission_create(body: MissionCreateRequest) -> dict[str, Any]:
    return _invoke(lambda: create_workspace_mission(
        source_workspace_id=body.source_workspace_id,
        goal=body.goal,
        risk=body.risk,
        source_task_id=body.source_task_id,
        source_run_id=body.source_run_id,
        changed_paths=body.changed_paths,
    ))


@router.get("/api/workspace-missions")
def mission_list(status: str | None = None, limit: int = 100) -> dict[str, Any]:
    items = list_workspace_missions(status=status, limit=limit)
    return {"items": items, "count": len(items)}


@router.get("/api/workspace-missions/{mission_id}")
def mission_show(mission_id: str) -> dict[str, Any]:
    record = get_workspace_mission(mission_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"mission not found: {mission_id}")
    return record


@router.post("/api/workspace-missions/{mission_id}/retry")
def mission_retry(mission_id: str) -> dict[str, Any]:
    return _invoke(lambda: retry_mission(mission_id))


@router.post("/api/workspace-missions/{mission_id}/cancel")
def mission_cancel(mission_id: str) -> dict[str, Any]:
    return _invoke(lambda: cancel_mission(mission_id))


@router.post("/api/workspace-missions/{mission_id}/verify")
def mission_verify(mission_id: str) -> dict[str, Any]:
    return _invoke(lambda: verify_mission(mission_id))


@router.post("/api/workspace-missions/{mission_id}/promote")
def mission_promote(mission_id: str) -> dict[str, Any]:
    return _invoke(lambda: promote_mission(mission_id))
