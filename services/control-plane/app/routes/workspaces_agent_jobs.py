"""Axon-owned agent terminal job routes (enqueue, read, cancel).

Split out of ``routes/workspaces.py`` per its ratchet target so job lifecycle
endpoints stay together as they grow.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.routes.schemas import EnqueueAgentTerminalJobRequest
from app.terminal.agent_jobs import (
    cancel_agent_terminal_job,
    enqueue_agent_terminal_job,
    get_agent_terminal_job,
    list_agent_terminal_jobs,
)
from app.workspace_catalog import WorkspaceNotFoundError, get_workspace_record

router = APIRouter()


def _assert_workspace(workspace_id: str) -> None:
    try:
        get_workspace_record(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _owned_job(workspace_id: str, job_id: str) -> dict[str, object]:
    record = get_agent_terminal_job(job_id)
    if record is None or str(record.get("workspace_id") or "") != str(workspace_id).strip():
        raise HTTPException(status_code=404, detail="agent terminal job not found")
    return record


@router.post("/api/workspaces/{workspace_id}/terminal/agent-jobs")
def workspace_terminal_agent_jobs_enqueue(
    workspace_id: str,
    body: EnqueueAgentTerminalJobRequest,
) -> dict[str, object]:
    """Enqueue a command into the Axon agent PTY (operator/agent callable)."""
    _assert_workspace(workspace_id)
    try:
        return enqueue_agent_terminal_job(
            workspace_id=workspace_id,
            command=body.command,
            run_id=body.run_id,
            stream_to_chat=body.stream_to_chat,
            thread_id=body.thread_id,
            message_id=body.message_id,
            source_workspace_id=body.source_workspace_id,
            timeout_seconds=body.timeout_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/workspaces/{workspace_id}/terminal/agent-jobs")
def workspace_terminal_agent_jobs_list(
    workspace_id: str,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, object]:
    _assert_workspace(workspace_id)
    items = list_agent_terminal_jobs(workspace_id, limit=limit)
    return {"workspace_id": workspace_id, "items": items, "count": len(items)}


@router.get("/api/workspaces/{workspace_id}/terminal/agent-jobs/{job_id}")
def workspace_terminal_agent_job_get(workspace_id: str, job_id: str) -> dict[str, object]:
    _assert_workspace(workspace_id)
    return _owned_job(workspace_id, job_id)


@router.delete("/api/workspaces/{workspace_id}/terminal/agent-jobs/{job_id}")
def workspace_terminal_agent_job_cancel(workspace_id: str, job_id: str) -> dict[str, object]:
    """Interrupt a running agent terminal job (operator or recovering agent)."""
    _assert_workspace(workspace_id)
    existing = _owned_job(workspace_id, job_id)
    record = cancel_agent_terminal_job(job_id) or existing
    return {"workspace_id": workspace_id, "cancelled": True, "job": record}


__all__ = ["router"]
