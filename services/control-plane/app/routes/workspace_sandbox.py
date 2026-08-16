"""Durable per-workspace composer Sandbox lifecycle routes."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, HTTPException

from app.cli_runtime.composer_sandbox import (
    DirtySandboxError,
    IsolationError,
    WorkspaceRootError,
    disable_sandbox,
    discard_sandbox,
    enable_sandbox,
    publish_sandbox,
    review_sandbox,
    sandbox_status,
)
from app.workspace_catalog import WorkspaceNotFoundError, get_workspace_record

router = APIRouter(tags=["workspace-sandbox"])


def _workspace_action(workspace_id: str, action: Callable[[str], dict[str, Any]]):
    try:
        get_workspace_record(workspace_id)
        return action(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DirtySandboxError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (IsolationError, WorkspaceRootError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/workspaces/{workspace_id}/sandbox")
def workspace_sandbox_status(workspace_id: str) -> dict[str, Any]:
    return _workspace_action(workspace_id, sandbox_status)


@router.post("/api/workspaces/{workspace_id}/sandbox/enable")
def workspace_sandbox_enable(workspace_id: str) -> dict[str, Any]:
    return _workspace_action(workspace_id, enable_sandbox)


@router.post("/api/workspaces/{workspace_id}/sandbox/disable")
def workspace_sandbox_disable(workspace_id: str) -> dict[str, Any]:
    return _workspace_action(workspace_id, disable_sandbox)


@router.get("/api/workspaces/{workspace_id}/sandbox/review")
def workspace_sandbox_review(workspace_id: str) -> dict[str, Any]:
    return _workspace_action(workspace_id, review_sandbox)


@router.post("/api/workspaces/{workspace_id}/sandbox/discard")
def workspace_sandbox_discard(workspace_id: str) -> dict[str, Any]:
    return _workspace_action(workspace_id, discard_sandbox)


@router.post("/api/workspaces/{workspace_id}/sandbox/publish")
def workspace_sandbox_publish(workspace_id: str) -> dict[str, Any]:
    return _workspace_action(workspace_id, publish_sandbox)
