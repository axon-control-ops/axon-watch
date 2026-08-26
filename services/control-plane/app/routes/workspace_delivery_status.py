"""Read-only workspace delivery policy status."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException

from app.workspace_delivery.config import get_workspace_delivery_policy

router = APIRouter(tags=["workspace-delivery"])


@router.get("/api/workspaces/{workspace_id}/delivery")
def workspace_delivery_status(workspace_id: str) -> dict[str, Any]:
    policy = get_workspace_delivery_policy(workspace_id)
    if policy is None or not policy.enabled:
        raise HTTPException(status_code=404, detail="workspace delivery is not configured")

    payload = asdict(policy)
    payload["workflow_names"] = list(policy.workflow_names)
    payload["protected_branches"] = list(policy.protected_branches)
    return {"workspace_id": workspace_id, "configured": True, "policy": payload}
