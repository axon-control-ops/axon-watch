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
from app.chat.thread_service import sync_thread_execution_access_notices
from app.chat.lane_b_agent import LaneBContext, generate_lane_b_result
from app.cli_runtime.approval_gate import full_access_requested
from app.persistence import attachment_store, chat_store
from app.instructions_engine import build_instruction_engine_user_prompt
from app.plain_text_to_instructions import compose_instructions_markdown
from app.routes.schemas import (
    GenerateInstructionsRequest,
    PostChatMessageRequest,
    SyncThreadExecutionAccessRequest,
)
from app.specialist_roles import validate_specialist_context

router = APIRouter()


@router.post("/api/composer/instructions")
def composer_instructions_generate(body: GenerateInstructionsRequest) -> dict[str, object]:
    source = body.content.strip()
    if not source:
        raise HTTPException(status_code=400, detail="A source request is required")
    try:
        specialist_context = validate_specialist_context(
            workspace_id=body.workspace_id,
            supplied=body.specialist_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    fallback = compose_instructions_markdown(source, None, specialist_context)
    result = generate_lane_b_result(
        context=LaneBContext(
            workspace_id=body.workspace_id,
            composer_mode="instructions",
            instructions_context=specialist_context,
        ),
        user_prompt=build_instruction_engine_user_prompt(source, specialist_context),
        runtime_target=body.runtime_target,
        runtime_model=body.runtime_model,
        execution_access="consultative",
        allow_git_dispatch=False,
    )
    raw_content = str(result.get("content") or "").strip()
    if not result.get("dispatched"):
        reason = str(result.get("reason") or "Instruction runtime unavailable")
        if fallback:
            return {
                "content": fallback,
                "runtime_id": str(result.get("runtime_id") or ""),
                "runtime_label": str(result.get("runtime_label") or "deterministic"),
                "fallback": True,
                "reason": reason,
                "specialist_role": specialist_context.role,
            }
        raise HTTPException(status_code=503, detail=reason)

    content = compose_instructions_markdown(source, raw_content, specialist_context)
    if not content:
        raise HTTPException(
            status_code=503,
            detail="The instruction model did not return valid Instructions markdown",
        )
    return {
        "content": content if content.endswith("\n") else f"{content}\n",
        "runtime_id": str(result.get("runtime_id") or ""),
        "runtime_label": str(result.get("runtime_label") or ""),
        "fallback": content == fallback,
        "specialist_role": specialist_context.role,
    }


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


@router.delete("/api/chat/threads/{thread_id}")
def chat_threads_delete(thread_id: str) -> dict[str, object]:
    try:
        return chat_store.delete_thread(thread_id)
    except chat_store.ChatThreadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/chat/threads/{thread_id}/history")
def chat_threads_history(thread_id: str, limit: int | None = None) -> dict[str, object]:
    try:
        if limit is not None:
            return get_chat_thread_history(thread_id, limit=limit)
        return get_chat_thread_history(thread_id)
    except chat_store.ChatThreadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/chat/threads/{thread_id}/execution-access-notices")
def chat_threads_sync_execution_access_notices(
    thread_id: str,
    body: SyncThreadExecutionAccessRequest,
) -> dict[str, object]:
    try:
        updated = sync_thread_execution_access_notices(thread_id, body.execution_access)
    except chat_store.ChatThreadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"thread_id": thread_id, "updated": updated}


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
