"""Chat message, thread, and attachment routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.auth.step_up import FULL_ACCESS_ACTION, reject_missing_step_up
from app.chat.service import (
    ChatValidationError,
    LaneBStreamJob,
    execute_lane_b_stream,
    get_chat_thread,
    get_chat_thread_history,
    post_chat_message,
)
from app.chat.stream_events import chat_thread_stream_response
from app.cli_runtime.approval_gate import full_access_requested
from app.persistence import attachment_store, chat_store
from app.routes.schemas import PostChatMessageRequest

router = APIRouter()


@router.post("/api/chat/messages")
def chat_messages_create(
    body: PostChatMessageRequest,
    background_tasks: BackgroundTasks,
    request: Request,
) -> dict[str, object]:
    if full_access_requested(body.execution_access):
        step_up_error = reject_missing_step_up(request, action=FULL_ACCESS_ACTION)
        if step_up_error is not None:
            raise HTTPException(
                status_code=403,
                detail=step_up_error,
                headers={"X-Axon-Step-Up-Required": FULL_ACCESS_ACTION},
            )
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
            kairo_session_id=body.kairo_session_id,
        )
        stream_job = payload.pop("_stream_job", None)
        if isinstance(stream_job, LaneBStreamJob):
            background_tasks.add_task(execute_lane_b_stream, stream_job)
        return payload
    except chat_store.ChatThreadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ChatValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/chat/threads/{thread_id}/stream")
def chat_threads_stream(thread_id: str):
    return chat_thread_stream_response(thread_id)


@router.get("/api/chat/threads/{thread_id}")
def chat_threads_show(thread_id: str) -> dict[str, object]:
    try:
        return get_chat_thread(thread_id)
    except chat_store.ChatThreadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/chat/threads/{thread_id}/history")
def chat_threads_history(thread_id: str) -> dict[str, object]:
    try:
        return get_chat_thread_history(thread_id)
    except chat_store.ChatThreadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/chat/attachments")
async def chat_attachments_upload(
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, object]:
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


@router.get("/api/chat/attachments/{attachment_id}")
def chat_attachments_show(attachment_id: str) -> FileResponse:
    try:
        record = attachment_store.require_attachment(attachment_id)
    except attachment_store.AttachmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    storage_path = str(record["storage_path"])
    mime_type = str(record["mime_type"])
    return FileResponse(
        storage_path,
        media_type=mime_type,
        filename=str(record["filename"]),
        content_disposition_type="inline" if mime_type.startswith("image/") else "attachment",
    )
