"""HTTP routes for durable IDE Plan artifacts."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.plans.service import PlanCaptureError, get_plan, list_plans

router = APIRouter(tags=["plans"])


@router.get("/api/plans")
def plans_index(workspace_id: str = Query(..., min_length=1)) -> dict[str, object]:
    try:
        items = list_plans(workspace_id)
    except PlanCaptureError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "items": [item.to_public_dict(include_content=False) for item in items],
        "count": len(items),
        "workspace_id": workspace_id,
    }


@router.get("/api/plans/{plan_id}")
def plans_get(
    plan_id: str,
    workspace_id: str = Query(..., min_length=1),
) -> dict[str, object]:
    try:
        record = get_plan(workspace_id, plan_id)
    except PlanCaptureError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status, detail=detail) from exc
    return record.to_public_dict(include_content=True)
