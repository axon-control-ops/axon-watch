"""Minimal FastAPI shell for the control-plane bootstrap slice."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.inbox_projection import build_inbox_response
from app.operator_briefing import build_operator_briefing
from app.runs.service import (
    approve_run,
    RunLifecycleError,
    RunNotFoundError,
    complete_run,
    create_run,
    get_run,
    list_runs,
    mark_review_ready,
    reject_run,
    resume_run,
    stop_run,
)
from app.runtime_summary import build_runtime_summary
from app.terminal.session_handler import handle_terminal_session
from app.workspace_catalog import get_workspace_record, list_workspace_records, WorkspaceNotFoundError


class CreateRunRequest(BaseModel):
    workspace_id: str
    mode: str = "agent"
    summary: str
    detail: str = ""
    requires_approval: bool = False


def _watch_base_url() -> str:
    return os.environ.get(
        "AXON_WATCH_WATCH_SERVICE_BASE_URL",
        "http://127.0.0.1:8788",
    )


app = FastAPI(
    title="Axon-X Control Plane",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.websocket("/api/workspaces/{workspace_id}/terminal")
async def workspace_terminal(websocket: WebSocket, workspace_id: str) -> None:
    await handle_terminal_session(websocket, workspace_id)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "service": "control-plane",
        "status": "ok",
        "mode": "bootstrap",
    }


@app.get("/api/readiness")
def readiness() -> dict[str, object]:
    return {
        "service": "control-plane",
        "status": "ready",
        "mode": "bootstrap",
        "watch_base_url": _watch_base_url(),
    }


@app.get("/api/runtime/summary")
def runtime_summary() -> dict[str, object]:
    return build_runtime_summary()


@app.get("/api/inbox")
def inbox() -> dict[str, object]:
    return build_inbox_response()


@app.get("/api/briefing")
def operator_briefing() -> dict[str, object]:
    return build_operator_briefing()


@app.get("/api/runs")
def runs_index() -> dict[str, Any]:
    items = list_runs()
    return {"items": items, "count": len(items)}


@app.get("/api/workspaces")
def workspaces_index() -> dict[str, Any]:
    items = list_workspace_records()
    return {"items": items, "count": len(items)}


@app.get("/api/workspaces/{workspace_id}")
def workspaces_show(workspace_id: str) -> dict[str, str]:
    try:
        return get_workspace_record(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/runs")
def runs_create(body: CreateRunRequest) -> dict[str, Any]:
    return create_run(
        workspace_id=body.workspace_id,
        mode=body.mode,
        summary=body.summary,
        detail=body.detail,
        requires_approval=body.requires_approval,
    )


@app.get("/api/runs/{run_id}")
def runs_show(run_id: str) -> dict[str, Any]:
    try:
        return get_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/complete")
def runs_complete(run_id: str) -> dict[str, Any]:
    try:
        return complete_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/review-ready")
def runs_review_ready(run_id: str) -> dict[str, Any]:
    try:
        return mark_review_ready(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/stop")
def runs_stop(run_id: str) -> dict[str, Any]:
    try:
        return stop_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/resume")
def runs_resume(run_id: str) -> dict[str, Any]:
    try:
        return resume_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/approve")
def runs_approve(run_id: str) -> dict[str, Any]:
    try:
        return approve_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/reject")
def runs_reject(run_id: str) -> dict[str, Any]:
    try:
        return reject_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
