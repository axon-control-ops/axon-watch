"""Minimal FastAPI shell for the control-plane bootstrap slice."""

from __future__ import annotations

import os
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Query, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

from app.chat.service import (
    ChatValidationError,
    LaneBStreamJob,
    create_workspace_chat_thread,
    execute_lane_b_stream,
    get_chat_thread,
    get_chat_thread_history,
    get_workspace_chat_thread,
    list_workspace_chat_threads,
    post_chat_message,
)
from app.persistence import attachment_store, chat_store, operator_presence_settings_store
from app.chat.stream_events import chat_thread_stream_response
from app.terminal.session_registry import (
    create_session,
    ensure_operator_session,
    list_sessions,
    serialize_session,
)
from app.inbox_signals import acknowledge_inbox_signals
from app.inbox_projection import build_inbox_response
from app.adapters.watch_client import (
    fetch_watch_connectors,
    fetch_watch_delivery_receipts,
    fetch_watch_events,
    fetch_watch_tunnel,
    get_watch_command,
    post_watch_command,
    post_watch_tunnel_action,
)
from app.operator_brain_graph import build_operator_brain_graph
from app.operator_briefing import build_operator_briefing
from app.operator_fleet_health import build_operator_fleet_health
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
from app.kairo_voice import generate_spoken_line, narration_allows_event
from app.kairo_conversation import converse_turn
from app.live_events import live_events_response
from app.cli_runtime.routes import (
    get_cursor_runtime_status,
    get_runtime_mcp_tools,
    get_runtime_status,
    post_codex_runtime_login_start,
    post_codex_runtime_logout,
    post_cursor_runtime_login_start,
    post_cursor_runtime_logout,
)
from app.vault.routes import (
    create_vault_secret,
    delete_vault_secret,
    export_vault_backup,
    export_vault_csv,
    get_vault_secret,
    get_vault_status,
    import_vault_backup,
    import_vault_monitor_keys,
    list_vault_secrets,
    update_vault_secret,
    vault_auto_unlock_disable,
    vault_auto_unlock_enable,
    vault_auto_unlock_status,
    vault_lock,
    vault_provider_keys,
    vault_setup,
    vault_unlock,
)
from app.data.routes import get_data_export, get_data_snapshot
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


class EditorSelectionContextRequest(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    text: str


class PostChatMessageRequest(BaseModel):
    workspace_id: str
    content: str
    thread_id: str | None = None
    run_id: str | None = None
    composer_mode: str | None = None
    active_file_path: str | None = None
    editor_selection: EditorSelectionContextRequest | None = None
    terminal_snippet: str | None = None
    attachment_ids: list[str] | None = None
    runtime_target: str | None = None
    runtime_model: str | None = None
    execution_access: str | None = None


class CreateWorkspaceChatThreadRequest(BaseModel):
    surface: str = "ide"
    run_id: str | None = None


class CreateTerminalSessionRequest(BaseModel):
    role: str = "operator"
    title: str | None = None
    run_id: str | None = None
    session_id: str | None = None


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


class VaultImportRequest(BaseModel):
    secrets: dict[str, str] = {}
    export_text: str = ""


class VaultSetupRequest(BaseModel):
    master_password: str


class VaultUnlockRequest(BaseModel):
    master_password: str
    totp_code: str
    remember_me: bool = False


class VaultSecretRequest(BaseModel):
    name: str
    category: str = "general"
    username: str = ""
    password: str = ""
    url: str = ""
    notes: str = ""


class VaultExportRequest(BaseModel):
    backup_password: str


class OperatorPresenceSettingsRequest(BaseModel):
    operator_persona_enabled: bool | None = None
    spoken_alerts_enabled: bool | None = None
    privacy_mode: bool | None = None
    mobile_compact_preferred: bool | None = None
    kairo_narration: str | None = None
    ide_voice_strip_enabled: bool | None = None
    hands_free_enabled: bool | None = None


class KairoSpeakRequest(BaseModel):
    event_type: str
    context: dict[str, Any] = {}
    session_id: str = "default"
    workspace_id: str = ""
    use_runtime: bool = True
    narration: str | None = None


class KairoConverseRequest(BaseModel):
    content: str
    session_id: str = "default"
    workspace_id: str = ""
    use_runtime: bool = False
    answer_tier: str = "fast"
    context_workspace_id: str = ""
    context_signal_id: str = ""
    context_node_id: str = ""


class KairoTtsRequest(BaseModel):
    text: str
    voice: str | None = None


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
async def workspace_terminal(
    websocket: WebSocket,
    workspace_id: str,
    session_id: str = Query("terminal-operator"),
    role: str = Query("operator"),
) -> None:
    await handle_terminal_session(
        websocket,
        workspace_id,
        session_id=session_id,
        role=role,
    )


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


@app.get("/api/runtime/status")
def runtime_status(force_refresh: bool = False) -> dict[str, object]:
    return get_runtime_status(force_refresh=force_refresh)


@app.post("/api/runtime/cursor/logout")
def cursor_runtime_logout() -> dict[str, object]:
    return post_cursor_runtime_logout()


@app.post("/api/runtime/cursor/login/start")
def cursor_runtime_login_start() -> dict[str, object]:
    return post_cursor_runtime_login_start()


@app.post("/api/runtime/codex/logout")
def codex_runtime_logout() -> dict[str, object]:
    return post_codex_runtime_logout()


@app.post("/api/runtime/codex/login/start")
def codex_runtime_login_start() -> dict[str, object]:
    return post_codex_runtime_login_start()


@app.get("/api/runtime/cursor/status")
def cursor_runtime_status(force_refresh: bool = False) -> dict[str, object]:
    return get_cursor_runtime_status(force_refresh=force_refresh)


@app.get("/api/runtime/mcp-tools")
def runtime_mcp_tools() -> dict[str, object]:
    return get_runtime_mcp_tools()


def _vault_http_error(exc: RuntimeError) -> HTTPException:
    message = str(exc)
    for code in (401, 423, 400, 404):
        if f"HTTP {code}" in message:
            detail = message.split(": ", 1)[-1] if ": " in message else message
            return HTTPException(status_code=code, detail=detail)
    return HTTPException(status_code=503, detail=message)


@app.get("/api/vault/status")
def vault_status_route() -> dict[str, object]:
    try:
        return get_vault_status()
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@app.get("/api/vault/provider-keys")
def vault_provider_keys_route() -> dict[str, object]:
    try:
        return vault_provider_keys()
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@app.post("/api/vault/setup")
def vault_setup_route(body: VaultSetupRequest) -> dict[str, object]:
    try:
        return vault_setup(body.master_password)
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@app.post("/api/vault/unlock")
def vault_unlock_route(body: VaultUnlockRequest) -> dict[str, object]:
    try:
        return vault_unlock(body.master_password, body.totp_code, remember_me=body.remember_me)
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@app.post("/api/vault/lock")
def vault_lock_route() -> dict[str, object]:
    try:
        return vault_lock()
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@app.get("/api/vault/auto-unlock/status")
def vault_auto_unlock_status_route() -> dict[str, object]:
    try:
        return vault_auto_unlock_status()
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@app.post("/api/vault/auto-unlock/enable")
def vault_auto_unlock_enable_route() -> dict[str, object]:
    try:
        return vault_auto_unlock_enable()
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@app.post("/api/vault/auto-unlock/disable")
def vault_auto_unlock_disable_route() -> dict[str, object]:
    try:
        return vault_auto_unlock_disable()
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@app.get("/api/vault/secrets")
def vault_secrets_list_route() -> list[dict[str, object]]:
    try:
        return list_vault_secrets()
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@app.get("/api/vault/secrets/{secret_id}")
def vault_secrets_show_route(secret_id: int) -> dict[str, object]:
    try:
        return get_vault_secret(secret_id)
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@app.post("/api/vault/secrets")
def vault_secrets_create_route(body: VaultSecretRequest) -> dict[str, object]:
    try:
        return create_vault_secret(body.model_dump())
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@app.put("/api/vault/secrets/{secret_id}")
def vault_secrets_update_route(secret_id: int, body: VaultSecretRequest) -> dict[str, object]:
    try:
        return update_vault_secret(secret_id, body.model_dump())
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@app.delete("/api/vault/secrets/{secret_id}")
def vault_secrets_delete_route(secret_id: int) -> dict[str, object]:
    try:
        return delete_vault_secret(secret_id)
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@app.post("/api/vault/export")
def vault_export_backup_route(body: VaultExportRequest):
    try:
        content, headers = export_vault_backup(body.backup_password)
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc
    disposition = headers.get("content-disposition", "")
    media_type = headers.get("content-type", "application/json")
    response_headers = {"Content-Disposition": disposition} if disposition else {}
    return Response(content=content, media_type=media_type, headers=response_headers)


@app.get("/api/vault/export/csv")
def vault_export_csv_route(format: str = Query(default="axon")):
    try:
        content, headers = export_vault_csv(format)
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc
    disposition = headers.get("content-disposition", "")
    media_type = headers.get("content-type", "text/csv; charset=utf-8")
    response_headers = {"Content-Disposition": disposition} if disposition else {}
    return Response(content=content, media_type=media_type, headers=response_headers)


@app.post("/api/vault/import")
async def vault_import_backup_route(
    backup_password: str = Form(""),
    mode: str = Form("merge"),
    file: UploadFile = File(...),
) -> dict[str, object]:
    try:
        raw = await file.read()
        return import_vault_backup(
            file_bytes=raw,
            filename=str(file.filename or "vault-import.bin"),
            backup_password=backup_password,
            mode=mode,
        )
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@app.post("/api/vault/import/monitor-keys")
def vault_import_monitor_keys_route(body: VaultImportRequest) -> dict[str, object]:
    try:
        return import_vault_monitor_keys(body.secrets, export_text=body.export_text)
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@app.get("/api/data/snapshot")
def data_snapshot_route(limit: int = 50) -> dict[str, object]:
    try:
        return get_data_snapshot(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/data/export")
def data_export_route(limit: int = 50) -> JSONResponse:
    try:
        payload = get_data_export(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": 'attachment; filename="axon-operator-data-export.json"',
        },
    )


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


@app.get("/api/tunnel/status")
def tunnel_status_index() -> dict[str, object]:
    payload = fetch_watch_tunnel()
    if payload is None:
        raise HTTPException(status_code=503, detail="watch tunnel status unavailable")
    return payload


@app.post("/api/tunnel/start")
def tunnel_start_index() -> dict[str, object]:
    payload = post_watch_tunnel_action("start")
    if payload is None:
        raise HTTPException(status_code=503, detail="watch tunnel start unavailable")
    return payload


@app.post("/api/tunnel/stop")
def tunnel_stop_index() -> dict[str, object]:
    payload = post_watch_tunnel_action("stop")
    if payload is None:
        raise HTTPException(status_code=503, detail="watch tunnel stop unavailable")
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
def operator_briefing(viewport_compact: bool = False, workspace_id: str = "") -> dict[str, object]:
    scoped_workspace_id = workspace_id.strip() or None
    return build_operator_briefing(
        viewport_compact=viewport_compact,
        workspace_id=scoped_workspace_id,
    )


@app.get("/api/operator/fleet-health")
def operator_fleet_health() -> dict[str, object]:
    return build_operator_fleet_health()


@app.get("/api/operator/brain-graph")
def operator_brain_graph() -> dict[str, object]:
    return build_operator_brain_graph()


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


@app.post("/api/kairo/speak")
def kairo_speak(body: KairoSpeakRequest) -> dict[str, str]:
    settings = operator_presence_settings_store.load_settings()
    narration = str(body.narration or settings.get("kairo_narration") or "minimal").strip().lower()
    if narration not in {"off", "minimal", "conversational"}:
        narration = "minimal"
    event_type = str(body.event_type or "").strip().lower()
    if not narration_allows_event(event_type, narration):  # type: ignore[arg-type]
        return {"line": "", "source": "skipped"}
    return generate_spoken_line(
        event_type=event_type,
        context=body.context,
        session_id=body.session_id,
        persona_enabled=bool(settings.get("operator_persona_enabled", True)),
        narration=narration,  # type: ignore[arg-type]
        workspace_id=body.workspace_id,
        use_runtime=body.use_runtime,
    )


@app.post("/api/kairo/tts")
def kairo_tts(body: KairoTtsRequest) -> dict[str, object]:
    import base64

    from app.azure_tts import (
        DEFAULT_AZURE_VOICE,
        azure_speech_configured,
        synthesize_azure_speech,
    )
    from app.cli_runtime.vault_keys import runtime_vault_posture

    trimmed = body.text.strip()
    if not trimmed:
        raise HTTPException(status_code=400, detail="text must not be empty")

    if not azure_speech_configured():
        posture = runtime_vault_posture()
        reason = "vault_locked" if not posture.get("unlocked") else "missing_key"
        return {
            "available": False,
            "provider": "browser",
            "reason": reason,
        }

    voice = str(body.voice or DEFAULT_AZURE_VOICE).strip() or DEFAULT_AZURE_VOICE
    synthesized = synthesize_azure_speech(trimmed, voice=voice)
    if not synthesized:
        return {
            "available": False,
            "provider": "browser",
            "reason": "synthesis_failed",
        }

    audio, content_type = synthesized
    return {
        "available": True,
        "provider": "azure",
        "voice": voice,
        "content_type": content_type,
        "audio_base64": base64.b64encode(audio).decode("ascii"),
    }


@app.get("/api/kairo/voice-log")
def kairo_voice_log(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, object]:
    from app.persistence.voice_transcript_store import list_recent_voice_transcripts

    return {"entries": list_recent_voice_transcripts(limit=limit)}


@app.post("/api/kairo/converse")
def kairo_converse(body: KairoConverseRequest) -> dict[str, object]:
    trimmed = body.content.strip()
    if not trimmed:
        raise HTTPException(status_code=400, detail="content must not be empty")
    try:
        return converse_turn(
            content=trimmed,
            session_id=body.session_id,
            workspace_id=body.workspace_id or None,
            use_runtime=body.use_runtime,
            answer_tier=body.answer_tier,
            context_workspace_id=body.context_workspace_id or None,
            context_signal_id=body.context_signal_id or None,
            context_node_id=body.context_node_id or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/live/events")
def live_events():
    return live_events_response()


@app.post("/api/chat/messages")
def chat_messages_create(
    body: PostChatMessageRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, object]:
    try:
        payload = post_chat_message(
            workspace_id=body.workspace_id,
            content=body.content,
            thread_id=body.thread_id,
            run_id=body.run_id,
            composer_mode=body.composer_mode,
            active_file_path=body.active_file_path,
            editor_selection=(
                body.editor_selection.model_dump() if body.editor_selection is not None else None
            ),
            terminal_snippet=body.terminal_snippet,
            attachment_ids=body.attachment_ids,
            runtime_target=body.runtime_target,
            runtime_model=body.runtime_model,
            execution_access=body.execution_access,
        )
        stream_job = payload.pop("_stream_job", None)
        if isinstance(stream_job, LaneBStreamJob):
            background_tasks.add_task(execute_lane_b_stream, stream_job)
        return payload
    except chat_store.ChatThreadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ChatValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/chat/threads/{thread_id}/stream")
def chat_threads_stream(thread_id: str):
    return chat_thread_stream_response(thread_id)


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


@app.post("/api/chat/attachments")
async def chat_attachments_upload(
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, object]:
    from datetime import datetime, timezone

    try:
        payload = await file.read()
        created_at = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        record = attachment_store.save_upload(
            workspace_id=workspace_id,
            filename=file.filename or "attachment",
            mime_type=file.content_type or "application/octet-stream",
            data=payload,
            created_at=created_at,
        )
        return attachment_store.serialize_attachment(record)
    except attachment_store.AttachmentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/chat/attachments/{attachment_id}")
def chat_attachments_show(attachment_id: str) -> FileResponse:
    try:
        record = attachment_store.require_attachment(attachment_id)
    except attachment_store.AttachmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    storage_path = str(record["storage_path"])
    return FileResponse(
        storage_path,
        media_type=str(record["mime_type"]),
        filename=str(record["filename"]),
    )


@app.get("/api/runs")
def runs_index() -> dict[str, Any]:
    items = list_runs()
    return {"items": items, "count": len(items)}


@app.get("/api/workspaces")
def workspaces_index(scope: str = "") -> dict[str, Any]:
    operator_surface = scope.strip().lower() == "operator"
    items = list_workspace_records(operator_surface=operator_surface)
    return {"items": items, "count": len(items), "scope": "operator" if operator_surface else "all"}


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
def workspace_chat_thread(workspace_id: str, surface: str = "operator") -> dict[str, object]:
    try:
        return get_workspace_chat_thread(workspace_id, thread_kind=surface)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ChatValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/workspaces/{workspace_id}/chat/threads")
def workspace_chat_threads(
    workspace_id: str,
    surface: str = "ide",
    limit: int = 25,
) -> dict[str, object]:
    try:
        return list_workspace_chat_threads(
            workspace_id,
            thread_kind=surface,
            limit=limit,
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ChatValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/workspaces/{workspace_id}/chat/threads")
def workspace_chat_threads_create(
    workspace_id: str,
    body: CreateWorkspaceChatThreadRequest,
) -> dict[str, object]:
    try:
        return create_workspace_chat_thread(
            workspace_id,
            thread_kind=body.surface,
            run_id=body.run_id,
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ChatValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/workspaces/{workspace_id}/terminal/sessions")
def workspace_terminal_sessions(workspace_id: str) -> dict[str, object]:
    try:
        get_workspace_record(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    ensure_operator_session(workspace_id)
    items = [serialize_session(record) for record in list_sessions(workspace_id)]
    return {"workspace_id": workspace_id, "items": items, "count": len(items)}


@app.post("/api/workspaces/{workspace_id}/terminal/sessions")
def workspace_terminal_sessions_create(
    workspace_id: str,
    body: CreateTerminalSessionRequest,
) -> dict[str, object]:
    try:
        get_workspace_record(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    record = create_session(
        workspace_id=workspace_id,
        role=body.role,
        title=body.title,
        run_id=body.run_id,
        session_id=body.session_id,
    )
    return serialize_session(record)


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
