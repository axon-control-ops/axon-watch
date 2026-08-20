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
from app.cli_runtime.sandbox_preview import (
    SandboxPreviewError,
    discover_previews,
    sandbox_preview_status,
    start_sandbox_preview,
    stop_preview_port,
    stop_sandbox_preview,
)
from app.routes.schemas import StartSandboxPreviewRequest
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
    except (IsolationError, WorkspaceRootError, SandboxPreviewError) as exc:
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


@router.get("/api/workspaces/{workspace_id}/sandbox/preview")
def workspace_sandbox_preview_status(workspace_id: str) -> dict[str, Any]:
    return _workspace_action(workspace_id, sandbox_preview_status)


@router.post("/api/workspaces/{workspace_id}/sandbox/preview")
def workspace_sandbox_preview_start(
    workspace_id: str,
    body: StartSandboxPreviewRequest | None = None,
) -> dict[str, Any]:
    """Run the workspace preview command inside the sandbox checkout."""
    request = body or StartSandboxPreviewRequest()
    return _workspace_action(
        workspace_id,
        lambda ws: start_sandbox_preview(ws, command=request.command, port=request.port),
    )


@router.delete("/api/workspaces/{workspace_id}/sandbox/preview")
def workspace_sandbox_preview_stop(workspace_id: str) -> dict[str, Any]:
    return _workspace_action(workspace_id, stop_sandbox_preview)


@router.get("/api/workspaces/{workspace_id}/sandbox/previews")
def workspace_sandbox_previews_list(workspace_id: str) -> dict[str, Any]:
    """Every listener on the preview port range, including orphaned ones."""
    return _workspace_action(workspace_id, discover_previews)


@router.delete("/api/workspaces/{workspace_id}/sandbox/previews/{port}")
def workspace_sandbox_previews_stop(workspace_id: str, port: int) -> dict[str, Any]:
    """Stop whatever holds a preview port. Range-restricted server side."""
    return _workspace_action(workspace_id, lambda ws: stop_preview_port(ws, port))
