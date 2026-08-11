"""Chat/composer orchestration for the control-plane thin slice."""

from __future__ import annotations
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.chat.command_intent import classify_command, expand_command_shortcuts
from app.chat.dispatch import build_command_dispatch_ack, resolve_command_dispatch
from app.chat.lane_b_agent import (
    EditorSelectionContext,
    LaneBContext,
    generate_lane_b_result,
    should_use_lane_b,
)
from app.chat.lane_b_persona_fast_path import (
    build_lane_b_persona_reply,
    post_lane_b_persona_message,
)
from app.chat.lane_b_fast_paths import post_image_redisplay_message, post_workspace_switch_message
from app.chat.lane_b_generated_image_actions import (
    bind_agent_generated_images,
    lane_b_open_file_ui_action,
    maybe_generated_image_redisplay_reply,
)
from app.cli_runtime.approval_gate import is_tool_capable_composer_mode, normalize_execution_access
from app.chat.lane_b_run_dispatch import resolve_lane_b_agent_run
from app.chat.orchestration import (
    build_agent_command_reply,
    orchestrate_command_run,
    orchestrate_resume_from_review,
)
from app.chat.reply_verification import verify_lane_b_reply
from app.chat.lane_b_thread_context import build_lane_b_thread_context_appendix
from app.cli_runtime.research_stream_blocks import normalize_transcript_content
from app.chat.progress_milestones import (
    publish_completion_milestone,
    persist_stream_delta,
    publish_stream_error_milestone,
)
from app.plans.service import maybe_attach_plan_artifact
from app.chat.stream_hub import close_chat_stream, clear_chat_stream_buffer, publish_chat_stream_event
from app.chat.thread_service import (
    create_workspace_chat_thread,
    get_chat_thread,
    get_chat_thread_history,
    get_workspace_chat_thread,
    list_workspace_chat_threads,
)
from app.chat.workspace_switch import (
    WorkspaceSwitchError,
    build_workspace_switch_reply,
    resolve_workspace_switch_intent,
    workspace_switch_ui_action,
)
from app.kairo.turn_memory import build_lane_b_memory_appendix, remember_turn
from app.persistence import attachment_store, chat_store
from app.runs.service import (
    RunLifecycleError,
    RunNotFoundError,
    append_run_execution_receipt,
    complete_run,
    fail_run,
    get_run,
    mark_review_ready,
)
from app.terminal.session_registry import ensure_agent_session, serialize_session
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root
from app.workspace_catalog import WorkspaceNotFoundError, get_workspace_record
from app.chat.lane_b_post_message import post_lane_b_message as _post_lane_b_message
from app.chat.lane_b_stream_execute import (
    LaneBStreamJob,
    execute_lane_b_stream,
    finalize_lane_b_agent_run,
    lane_b_system_content,
    remember_lane_b_turn,
)

_finalize_lane_b_agent_run = finalize_lane_b_agent_run
_lane_b_system_content = lane_b_system_content
_remember_lane_b_turn = remember_lane_b_turn


class ChatValidationError(ValueError):
    pass


_KAIRO_CONTINUATION_RE = re.compile(
    r"\b(continue|pick up|resume|as we discussed|the plan|that in the ide)\b",
    re.IGNORECASE,
)
_KAIRO_HANDOFF_TASK_RE = re.compile(r'^Investigate signal "', re.IGNORECASE)


def _lane_b_memory_appendix(*, content: str, kairo_session_id: str | None) -> str | None:
    clean_session_id = str(kairo_session_id or "").strip()
    if not clean_session_id:
        return None
    trimmed = content.strip()
    if not (_KAIRO_CONTINUATION_RE.search(trimmed) or _KAIRO_HANDOFF_TASK_RE.match(trimmed)):
        return None
    appendix = build_lane_b_memory_appendix(clean_session_id, max_chars=800)
    return appendix or None


def _compose_lane_b_memory_appendix(
    *,
    thread_id: str,
    content: str,
    kairo_session_id: str | None,
    composer_mode: str,
) -> str | None:
    thread_appendix = build_lane_b_thread_context_appendix(
        chat_store.list_thread_messages(thread_id)
    )
    kairo_appendix = (
        _lane_b_memory_appendix(content=content, kairo_session_id=kairo_session_id)
        if is_tool_capable_composer_mode(composer_mode)
        else None
    )
    parts = [part.strip() for part in (thread_appendix, kairo_appendix) if part and str(part).strip()]
    if not parts:
        return None
    return "\n\n".join(parts)


def _coerce_attachment_ids(raw: list[str] | None) -> list[str]:
    if not raw:
        return []
    seen: set[str] = set()
    attachment_ids: list[str] = []
    for item in raw:
        clean = str(item or "").strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        attachment_ids.append(clean)
    return attachment_ids


def _attachment_paths_for_ids(attachment_ids: list[str], workspace_id: str) -> tuple[str, ...]:
    if not attachment_ids:
        return ()
    paths: list[str] = []
    for attachment_id in attachment_ids:
        record = attachment_store.get_attachment(attachment_id)
        if record is None:
            raise ChatValidationError(f"attachment not found: {attachment_id}")
        if record["workspace_id"] != workspace_id:
            raise ChatValidationError("attachment does not belong to workspace")
        if record["message_id"]:
            raise ChatValidationError("attachment is already linked to a message")
        paths.append(str(record["storage_path"]))
    return tuple(paths)


def _bind_message_attachments(
    *,
    attachment_ids: list[str],
    workspace_id: str,
    message_id: str,
    thread_id: str,
) -> tuple[list[dict[str, object]], tuple[str, ...]]:
    if not attachment_ids:
        return [], ()
    try:
        bound = attachment_store.bind_attachments_to_message(
            attachment_ids=attachment_ids,
            workspace_id=workspace_id,
            message_id=message_id,
            thread_id=thread_id,
        )
    except attachment_store.AttachmentNotFoundError as exc:
        raise ChatValidationError(str(exc)) from exc
    except attachment_store.AttachmentValidationError as exc:
        raise ChatValidationError(str(exc)) from exc
    serialized = [attachment_store.serialize_attachment(item) for item in bound]
    paths = tuple(str(item["storage_path"]) for item in bound)
    return serialized, paths


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _lane_b_streaming_enabled() -> bool:
    return os.environ.get("AXON_WATCH_LANE_B_STREAMING", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }


def _new_message_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _normalize_thread_kind(thread_kind: str | None) -> str:
    kind = str(thread_kind or "operator").strip().lower() or "operator"
    return kind if kind in {"operator", "ide"} else "operator"


def _resolve_chat_thread(
    *,
    workspace_id: str,
    thread_id: str | None,
    thread_kind: str,
    run_id: str | None,
    created_at: str,
) -> tuple[dict[str, object], str]:
    kind = _normalize_thread_kind(thread_kind)
    if thread_id:
        thread = chat_store.get_thread(thread_id)
        if thread is None:
            raise chat_store.ChatThreadNotFoundError(f"thread not found: {thread_id}")
        if thread["workspace_id"] != workspace_id:
            raise ChatValidationError("thread_id does not belong to workspace_id")
        existing_kind = _normalize_thread_kind(str(thread.get("thread_kind") or "operator"))
        if existing_kind != kind:
            raise ChatValidationError("thread_id does not match conversation surface")
        return thread, thread_id

    thread = chat_store.get_latest_thread_for_workspace(workspace_id, thread_kind=kind)
    if thread is not None:
        return thread, str(thread["thread_id"])

    created = chat_store.create_thread(
        workspace_id=workspace_id,
        run_id=run_id,
        created_at=created_at,
        thread_kind=kind,
    )
    return created, str(created["thread_id"])


def _validate_workspace(workspace_id: str) -> None:
    try:
        get_workspace_record(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise ChatValidationError(str(exc)) from exc


def _coerce_editor_selection(raw: dict[str, object] | None) -> EditorSelectionContext | None:
    if not raw:
        return None
    text = str(raw.get("text") or "").strip()
    file_path = str(raw.get("file_path") or "").strip()
    if not text or not file_path:
        return None
    return EditorSelectionContext(
        file_path=file_path,
        start_line=max(1, int(raw.get("start_line") or 1)),
        end_line=max(1, int(raw.get("end_line") or 1)),
        text=text[:4000],
    )


def _coerce_terminal_snippet(raw: str | None) -> str | None:
    snippet = str(raw or "").strip()
    if not snippet:
        return None
    return snippet[:4000]


def post_chat_message(
    *,
    workspace_id: str,
    content: str,
    thread_id: str | None = None,
    run_id: str | None = None,
    composer_mode: str | None = None,
    active_file_path: str | None = None,
    editor_selection: dict[str, object] | None = None,
    terminal_snippet: str | None = None,
    attachment_ids: list[str] | None = None,
    runtime_target: str | None = None,
    runtime_model: str | None = None,
    execution_access: str | None = None,
    kairo_session_id: str | None = None,
) -> dict[str, object]:
    trimmed = content.strip()
    if not trimmed:
        raise ChatValidationError("content must not be empty")

    _validate_workspace(workspace_id)
    created_at = _utc_now()
    normalized_attachment_ids = _coerce_attachment_ids(attachment_ids)
    normalized = expand_command_shortcuts(trimmed)
    intent = classify_command(normalized)
    if should_use_lane_b(composer_mode=composer_mode, command_intent=intent):
        return _post_lane_b_message(
            workspace_id=workspace_id,
            content=trimmed,
            thread_id=thread_id,
            run_id=run_id,
            composer_mode=str(composer_mode or "agent"),
            active_file_path=active_file_path,
            editor_selection=_coerce_editor_selection(editor_selection),
            terminal_snippet=_coerce_terminal_snippet(terminal_snippet),
            attachment_ids=normalized_attachment_ids,
            runtime_target=runtime_target,
            runtime_model=runtime_model,
            execution_access=normalize_execution_access(execution_access),
            kairo_session_id=kairo_session_id,
            created_at=created_at,
        )
    if intent == "resume_from_review":
        run_record, execution = orchestrate_resume_from_review(workspace_id=workspace_id)
        dispatch_run_id = str(run_record["run_id"])
        dispatched = False
    else:
        dispatch_run_id, run_record, dispatched = resolve_command_dispatch(
            workspace_id=workspace_id,
            content=normalized,
            run_id=run_id,
        )
        run_record, execution = orchestrate_command_run(
            workspace_id=workspace_id,
            content=normalized,
            run_record=run_record,
            dispatched=dispatched,
        )
    ack_content = build_command_dispatch_ack(
        run_id=dispatch_run_id,
        phase=str(run_record["phase"]),
        dispatched=dispatched,
        execution=execution,
    )
    agent_content = build_agent_command_reply(
        content=normalized,
        run_record=run_record,
        dispatched=dispatched,
        execution=execution,
    )

    if thread_id:
        thread, thread_id = _resolve_chat_thread(
            workspace_id=workspace_id,
            thread_id=thread_id,
            thread_kind="operator",
            run_id=dispatch_run_id,
            created_at=created_at,
        )
    else:
        thread, thread_id = _resolve_chat_thread(
            workspace_id=workspace_id,
            thread_id=None,
            thread_kind="operator",
            run_id=dispatch_run_id,
            created_at=created_at,
        )

    operator_message = chat_store.save_message(
        {
            "message_id": _new_message_id("message_operator"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": dispatch_run_id,
            "role": "operator",
            "content": trimmed,
            "created_at": created_at,
        }
    )
    operator_attachments, _ = _bind_message_attachments(
        attachment_ids=normalized_attachment_ids,
        workspace_id=workspace_id,
        message_id=str(operator_message["message_id"]),
        thread_id=thread_id,
    )
    if operator_attachments:
        operator_message = {**operator_message, "attachments": operator_attachments}
    system_message = chat_store.save_message(
        {
            "message_id": _new_message_id("message_system"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": dispatch_run_id,
            "role": "system",
            "content": ack_content,
            "created_at": created_at,
        }
    )
    agent_message = chat_store.save_message(
        {
            "message_id": _new_message_id("message_agent"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": dispatch_run_id,
            "role": "agent",
            "content": agent_content,
            "created_at": created_at,
        }
    )

    return {
        "thread_id": thread_id,
        "messages": [operator_message, system_message, agent_message],
        "run_id": dispatch_run_id,
        "dispatched": dispatched,
        "run": run_record,
        **(
            {"ui_action": execution.ui_action}
            if execution is not None and getattr(execution, "ui_action", None)
            else {}
        ),
    }
