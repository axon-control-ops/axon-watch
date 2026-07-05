"""Minimal FastAPI shell for the control-plane bootstrap slice."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.chat.service import (
    ChatValidationError,
    get_chat_thread,
    get_chat_thread_history,
    get_workspace_chat_thread,
    post_chat_message,
)
from app.inbox_projection import build_inbox_response
from app.inbox_signals import acknowledge_inbox_signals
from app.adapters.watch_client import (
    fetch_watch_connectors,
    fetch_watch_delivery_receipts,
    fetch_watch_events,
    get_watch_command,
    post_watch_command,
)
from app.persistence import chat_store, operator_presence_settings_store
from app.operator_briefing import build_operator_briefing
from app.runs.service import (
    approve_run,
    RunLifecycleError,
    RunNotFoundError,
    complete_run,
    create_run,
    get_run,
    get_run_history,
    list_runs,
    mark_review_ready,
    reject_run,
    resume_run,
    stop_run,
)
from app.runtime_summary import build_runtime_summary
from app.terminal.session_handler import handle_terminal_session
from app.workspace_catalog import get_workspace_record, list_workspace_records, WorkspaceNotFoundError
from app.workspace_handoffs import (
    WorkspaceHandoffError,
    create_workspace_handoff,
    list_workspace_handoffs,
)
from app.live_events import live_events_response
from app.workspace_files import (
    WorkspaceFileError,
    list_workspace_files,
    rename_workspace_file,
    read_workspace_file,
    write_workspace_file,
)


class WriteWorkspaceFileRequest(BaseModel):
    content: str


class RenameWorkspaceFileRequest(BaseModel):
    new_path: str


class CreateRunRequest(BaseModel):
    workspace_id: str
    mode: str = "agent"
    summary: str
    detail: str = ""
    requires_approval: bool = False


class PostChatMessageRequest(BaseModel):
    workspace_id: str
    content: str
    thread_id: str | None = None
    run_id: str | None = None
    composer_mode: str | None = None
    active_file_path: str | None = None


class CreateWorkspaceHandoffRequest(BaseModel):
    target_workspace_id: str
    task: str
    reason: str = ""


class WatchCommandRequest(BaseModel):
    command_id: str | None = None
    command_type: str
    target_type: str = ""
    target_id: str = ""
    requested_by: str = "operator"
    payload: dict[str, object] | None = None
    requested_at: str | None = None


class AcknowledgeInboxSignalsRequest(BaseModel):
    signal_ids: list[str]


class OperatorPresenceSettingsRequest(BaseModel):
    operator_persona_enabled: bool | None = None
    spoken_alerts_enabled: bool | None = None
    privacy_mode: bool | None = None
    mobile_compact_preferred: bool | None = None


def _watch_base_url() -> str:
    return os.environ.get(
        "AXON_WATCH_WATCH_SERVICE_BASE_URL",
        "http://127.0.0.1:8788",
    )


def _deployment_mode() -> str:
    return os.environ.get("AXON_WATCH_DEPLOYMENT_MODE", "bootstrap").strip() or "bootstrap"


def _state_dir() -> str:
    return os.environ.get("AXON_WATCH_STATE_DIR", "./.local/state")


def _public_base_url() -> str:
    return os.environ.get(
        "AXON_WATCH_PUBLIC_BASE_URL",
        "http://127.0.0.1:4173",
    ).strip() or "http://127.0.0.1:4173"


def _cors_origins() -> list[str]:
    raw = os.environ.get("AXON_WATCH_CORS_ORIGINS", "").strip()
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return [
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ]


app = FastAPI(
    title="Axon-X Control Plane",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["GET", "POST", "PUT"],
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
        "mode": _deployment_mode(),
        "watch_base_url": _watch_base_url(),
        "state_dir": _state_dir(),
        "public_base_url": _public_base_url(),
    }


@app.get("/api/runtime/summary")
def runtime_summary() -> dict[str, object]:
    return build_runtime_summary()


@app.get("/api/inbox")
def inbox() -> dict[str, object]:
    return build_inbox_response()


@app.post("/api/inbox/signals/acknowledge")
def inbox_signals_acknowledge(body: AcknowledgeInboxSignalsRequest) -> dict[str, object]:
    result = acknowledge_inbox_signals(body.signal_ids)
    if not result.get("accepted"):
        raise HTTPException(
            status_code=503,
            detail=str(result.get("error", "signal acknowledgement unavailable")),
        )
    return result


@app.get("/api/connectors")
def connectors_index() -> dict[str, object]:
    payload = fetch_watch_connectors()
    if payload is None:
        raise HTTPException(status_code=503, detail="watch connectors unavailable")
    return payload


@app.post("/api/watch/commands")
def watch_commands_create(body: WatchCommandRequest) -> dict[str, object]:
    payload = post_watch_command(body.model_dump())
    if payload is None:
        raise HTTPException(status_code=503, detail="watch command submission unavailable")
    return payload


@app.get("/api/watch/commands/{command_id}")
def watch_commands_show(command_id: str) -> dict[str, object]:
    payload = get_watch_command(command_id)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"watch command not found: {command_id}")
    return payload


@app.get("/api/watch/events")
def watch_events_index(limit: int = 20, cursor: str = "") -> dict[str, object]:
    payload = fetch_watch_events(limit=limit, cursor=cursor)
    if payload is None:
        raise HTTPException(status_code=503, detail="watch events unavailable")
    return payload


@app.get("/api/delivery/receipts")
def delivery_receipts_index(limit: int = 20, cursor: str = "") -> dict[str, object]:
    payload = fetch_watch_delivery_receipts(limit=limit, cursor=cursor)
    if payload is None:
        raise HTTPException(status_code=503, detail="watch delivery receipts unavailable")
    return payload


@app.get("/api/briefing")
def operator_briefing(viewport_compact: bool = False) -> dict[str, object]:
    return build_operator_briefing(viewport_compact=viewport_compact)


@app.get("/api/operator-presence/settings")
def operator_presence_settings_get() -> dict[str, object]:
    settings = operator_presence_settings_store.load_settings()
    return {"settings": settings}


@app.put("/api/operator-presence/settings")
def operator_presence_settings_put(body: OperatorPresenceSettingsRequest) -> dict[str, object]:
    current = operator_presence_settings_store.load_settings()
    patch = body.model_dump(exclude_none=True)
    current.update(patch)
    return operator_presence_settings_store.save_settings(current)


@app.get("/api/live/events")
def live_events():
    return live_events_response()


@app.post("/api/chat/messages")
def chat_messages_create(body: PostChatMessageRequest) -> dict[str, object]:
    try:
        return post_chat_message(
            workspace_id=body.workspace_id,
            content=body.content,
            thread_id=body.thread_id,
            run_id=body.run_id,
            composer_mode=body.composer_mode,
            active_file_path=body.active_file_path,
        )
    except chat_store.ChatThreadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ChatValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/chat/threads/{thread_id}")
def chat_threads_show(thread_id: str) -> dict[str, object]:
    try:
        return get_chat_thread(thread_id)
    except chat_store.ChatThreadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/chat/threads/{thread_id}/history")
def chat_threads_history(thread_id: str) -> dict[str, object]:
    try:
        return get_chat_thread_history(thread_id)
    except chat_store.ChatThreadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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


@app.post("/api/workspaces/{workspace_id}/handoffs")
def workspace_handoffs_create(
    workspace_id: str,
    body: CreateWorkspaceHandoffRequest,
) -> dict[str, object]:
    try:
        return create_workspace_handoff(
            source_workspace_id=workspace_id,
            target_workspace_id=body.target_workspace_id,
            task=body.task,
            reason=body.reason,
        )
    except WorkspaceHandoffError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@app.get("/api/workspaces/{workspace_id}/handoffs")
def workspace_handoffs_index(workspace_id: str) -> dict[str, object]:
    try:
        items = list_workspace_handoffs(workspace_id)
        return {"workspace_id": workspace_id, "items": items, "count": len(items)}
    except WorkspaceHandoffError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@app.get("/api/workspaces/{workspace_id}/chat/thread")
def workspace_chat_thread(workspace_id: str) -> dict[str, object]:
    try:
        return get_workspace_chat_thread(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ChatValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/workspaces/{workspace_id}/files")
def workspace_files_index(workspace_id: str) -> dict[str, object]:
    try:
        items = list_workspace_files(workspace_id)
        return {"workspace_id": workspace_id, "items": items, "count": len(items)}
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkspaceFileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/workspaces/{workspace_id}/files/{file_path:path}")
def workspace_files_show(workspace_id: str, file_path: str) -> dict[str, object]:
    try:
        return read_workspace_file(workspace_id, file_path)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkspaceFileError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/api/workspaces/{workspace_id}/files/{file_path:path}")
def workspace_files_update(
    workspace_id: str,
    file_path: str,
    body: WriteWorkspaceFileRequest,
) -> dict[str, object]:
    try:
        return write_workspace_file(workspace_id, file_path, body.content)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkspaceFileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/workspaces/{workspace_id}/files/{file_path:path}/rename")
def workspace_files_rename(
    workspace_id: str,
    file_path: str,
    body: RenameWorkspaceFileRequest,
) -> dict[str, object]:
    try:
        return rename_workspace_file(workspace_id, file_path, body.new_path)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkspaceFileError as exc:
        status_code = 409 if "already exists" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


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


@app.get("/api/runs/{run_id}/history")
def runs_history(run_id: str) -> dict[str, Any]:
    try:
        return get_run_history(run_id)
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
