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
from app.cli_runtime.approval_gate import normalize_execution_access
from app.chat.lane_b_run_dispatch import resolve_lane_b_agent_run
from app.chat.orchestration import (
    build_agent_command_reply,
    orchestrate_command_run,
    orchestrate_resume_from_review,
)
from app.chat.reply_verification import verify_lane_b_reply
from app.chat.lane_b_thread_context import build_lane_b_thread_context_appendix
from app.chat.progress_milestones import (
    publish_completion_milestone,
    persist_stream_delta,
    publish_stream_error_milestone,
)
from app.chat.stream_hub import close_chat_stream, clear_chat_stream_buffer, publish_chat_stream_event
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


@dataclass(frozen=True)
class LaneBStreamJob:
    thread_id: str
    agent_message_id: str
    system_message_id: str
    workspace_id: str
    content: str
    composer_mode: str
    active_file_path: str | None
    editor_selection: EditorSelectionContext | None
    terminal_snippet: str | None
    image_paths: tuple[str, ...]
    runtime_target: str | None
    runtime_model: str | None
    execution_access: str
    dispatch_run_id: str
    created_at: str
    memory_appendix: str | None = None
    kairo_session_id: str | None = None


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
        if composer_mode == "agent"
        else None
    )
    parts = [part.strip() for part in (thread_appendix, kairo_appendix) if part and str(part).strip()]
    if not parts:
        return None
    return "\n\n".join(parts)


def _remember_lane_b_turn(
    *,
    kairo_session_id: str | None,
    operator_content: str,
    agent_content: str,
) -> None:
    session = str(kairo_session_id or "").strip()
    if not session:
        return
    if str(operator_content or "").strip():
        remember_turn(session, "user", operator_content)
    if str(agent_content or "").strip():
        remember_turn(session, "assistant", agent_content)


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


def _enrich_message_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    message_ids = [str(item.get("message_id") or "") for item in records]
    grouped = attachment_store.list_attachments_for_messages(message_ids)
    enriched: list[dict[str, object]] = []
    for record in records:
        next_record = dict(record)
        message_id = str(record.get("message_id") or "")
        attachments = grouped.get(message_id, [])
        if attachments:
            next_record["attachments"] = [
                attachment_store.serialize_attachment(item) for item in attachments
            ]
        enriched.append(next_record)
    return enriched


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
    }


def _lane_b_system_content(
    *,
    composer_mode: str,
    dispatch_run_id: str,
    dispatched: bool,
    run_phase: str | None = None,
    streaming: bool = False,
) -> str:
    if streaming:
        if composer_mode == "agent" and dispatch_run_id:
            return f"Lane B (agent) — streaming runtime reply for run {dispatch_run_id}."
        return f"Lane B ({composer_mode}) — generating reply…"

    if composer_mode == "agent" and dispatch_run_id:
        if run_phase == "awaiting_approval":
            if dispatched:
                return (
                    f"Lane B (agent) recorded run {dispatch_run_id} at the approval boundary. "
                    "Consultative runtime reply only; approve the run before tool execution."
                )
            return (
                f"Lane B (agent) recorded run {dispatch_run_id} at the approval boundary. "
                "Approve the run before tool execution starts."
            )
        if dispatched:
            return (
                f"Lane B (agent) dispatched to runtime fabric for run {dispatch_run_id} "
                f"(phase {run_phase or 'executing'})."
            )
        return (
            f"Lane B (agent) recorded run {dispatch_run_id}, but runtime dispatch fell back "
            f"to a consultative reply (phase {run_phase or 'executing'})."
        )
    return f"Lane B ({composer_mode}) — conversational reply only; no command dispatch."


def _finalize_lane_b_agent_run(
    *,
    dispatch_run_id: str,
    lane_b_result: dict[str, object],
) -> tuple[bool, dict[str, object] | None]:
    dispatched = bool(lane_b_result.get("dispatched"))
    runtime_label = str(lane_b_result.get("runtime_label") or "runtime fallback")
    reason = str(lane_b_result.get("reason") or "").strip()
    receipt_summary = (
        f"Lane B agent reply generated via {runtime_label}"
        if dispatched
        else f"Lane B agent fallback reply generated ({reason or 'runtime unavailable'})"
    )
    run_record = append_run_execution_receipt(
        dispatch_run_id,
        receipt_type="runtime_dispatch",
        receipt_summary=receipt_summary,
        actor="cli_runtime",
        success=dispatched,
        intent="lane_b_agent",
    )
    # Successful agent turns auto-complete: Full Access consent already covers
    # them, so Mission Control should not queue routine runs for manual review.
    # Failed dispatches fail closed — the error is already in the thread.
    try:
        if dispatched:
            run_record = complete_run(dispatch_run_id)
        else:
            run_record = fail_run(
                dispatch_run_id,
                receipt_summary=receipt_summary,
            )
    except RunLifecycleError:
        pass
    return dispatched, run_record


def execute_lane_b_stream(job: LaneBStreamJob) -> None:
    context = LaneBContext(
        workspace_id=job.workspace_id,
        composer_mode=job.composer_mode,
        active_file_path=job.active_file_path,
        editor_selection=job.editor_selection,
        terminal_snippet=job.terminal_snippet,
        image_paths=job.image_paths,
        memory_appendix=job.memory_appendix,
    )
    dispatched = False
    run_record = None
    lane_b_result: dict[str, object] = {}
    milestone_content = ""

    def on_chunk(accumulated: str, delta: str) -> None:
        nonlocal milestone_content
        milestone_content = persist_stream_delta(
            thread_id=job.thread_id,
            message_id=job.agent_message_id,
            previous_content=milestone_content,
            accumulated=accumulated,
            delta=delta,
            updated_at=_utc_now(),
        )

    try:
        lane_b_result = generate_lane_b_result(
            context=context,
            user_prompt=job.content,
            run_id=job.dispatch_run_id,
            runtime_target=job.runtime_target,
            runtime_model=job.runtime_model,
            execution_access=job.execution_access,
            on_chunk=on_chunk,
        )
        agent_content = str(lane_b_result.get("content") or "")
        execution_tier = str(lane_b_result.get("execution_tier") or "consultative")
        try:
            workspace_root = resolve_workspace_root(job.workspace_id)
        except WorkspaceRootError:
            workspace_root = None
        run_started_epoch = None
        if job.dispatch_run_id:
            try:
                run_record_for_verify = get_run(job.dispatch_run_id)
                started_at = str(run_record_for_verify.get("started_at") or "")
                if started_at.endswith("Z"):
                    run_started_epoch = datetime.fromisoformat(
                        started_at.replace("Z", "+00:00")
                    ).timestamp()
            except RunNotFoundError:
                run_started_epoch = None
        agent_content, verification_warnings = verify_lane_b_reply(
            agent_content,
            execution_tier=execution_tier,
            workspace_root=workspace_root,
            run_started_epoch=run_started_epoch,
        )
        from app.cli_runtime.research_stream_blocks import normalize_transcript_content

        agent_content = normalize_transcript_content(agent_content)
        updated_at = _utc_now()
        chat_store.update_message_content(
            message_id=job.agent_message_id,
            content=agent_content,
            updated_at=updated_at,
        )
        _remember_lane_b_turn(
            kairo_session_id=job.kairo_session_id,
            operator_content=job.content,
            agent_content=agent_content,
        )

        if job.composer_mode == "agent" and job.dispatch_run_id:
            dispatched, run_record = _finalize_lane_b_agent_run(
                dispatch_run_id=job.dispatch_run_id,
                lane_b_result=lane_b_result,
            )
            if verification_warnings:
                append_run_execution_receipt(
                    job.dispatch_run_id,
                    receipt_type="reply_verification",
                    receipt_summary="; ".join(verification_warnings),
                    actor="reply_verification",
                    success=False,
                    intent="lane_b_agent",
                )
            system_content = _lane_b_system_content(
                composer_mode=job.composer_mode,
                dispatch_run_id=job.dispatch_run_id,
                dispatched=dispatched,
                run_phase=str(run_record["phase"]) if run_record is not None else None,
            )
        else:
            system_content = _lane_b_system_content(
                composer_mode=job.composer_mode,
                dispatch_run_id=job.dispatch_run_id,
                dispatched=bool(lane_b_result.get("dispatched")),
            )

        chat_store.update_message_content(
            message_id=job.system_message_id,
            content=system_content,
            updated_at=updated_at,
        )
        publish_completion_milestone(
            thread_id=job.thread_id,
            message_id=job.agent_message_id,
            verification_warnings=verification_warnings,
            run_record=run_record,
        )
        agent_attachments = bind_agent_generated_images(
            workspace_id=job.workspace_id,
            message_id=job.agent_message_id,
            thread_id=job.thread_id,
            lane_b_result=lane_b_result,
            agent_content=agent_content,
            created_at=updated_at,
        )
        ui_action = lane_b_open_file_ui_action(
            operator_content=job.content,
            workspace_id=job.workspace_id,
            thread_id=job.thread_id,
            lane_b_result=lane_b_result,
            agent_content=agent_content,
        )
        publish_chat_stream_event(
            job.thread_id,
            {
                "type": "chat_stream_done",
                "thread_id": job.thread_id,
                "message_id": job.agent_message_id,
                "content": agent_content,
                "system_message_id": job.system_message_id,
                "system_content": system_content,
                "dispatched": dispatched,
                "run_id": job.dispatch_run_id,
                "run": run_record,
                **({"attachments": agent_attachments} if agent_attachments else {}),
                **({"ui_action": ui_action} if ui_action else {}),
            },
        )
    except Exception as exc:
        fallback = str(exc).strip() or "runtime stream failed"
        updated_at = _utc_now()
        chat_store.update_message_content(
            message_id=job.agent_message_id,
            content=fallback,
            updated_at=updated_at,
        )
        run_record = None
        if job.composer_mode == "agent" and job.dispatch_run_id:
            try:
                run_record = fail_run(
                    job.dispatch_run_id,
                    receipt_summary=f"Lane B stream failed: {fallback}",
                )
            except RunLifecycleError:
                run_record = None
        publish_stream_error_milestone(
            thread_id=job.thread_id,
            message_id=job.agent_message_id,
            error=fallback,
        )
        publish_chat_stream_event(
            job.thread_id,
            {
                "type": "chat_stream_error",
                "thread_id": job.thread_id,
                "message_id": job.agent_message_id,
                "content": fallback,
                "error": fallback,
                "run_id": job.dispatch_run_id,
                "run": run_record,
            },
        )
    finally:
        close_chat_stream(job.thread_id)
        clear_chat_stream_buffer(job.thread_id)


def _post_lane_b_message(
    *,
    workspace_id: str,
    content: str,
    thread_id: str | None,
    run_id: str | None,
    composer_mode: str,
    active_file_path: str | None,
    editor_selection: EditorSelectionContext | None,
    terminal_snippet: str | None,
    attachment_ids: list[str],
    runtime_target: str | None,
    runtime_model: str | None,
    execution_access: str,
    kairo_session_id: str | None,
    created_at: str,
) -> dict[str, object]:
    try:
        switch_intent = resolve_workspace_switch_intent(content)
    except WorkspaceSwitchError as exc:
        raise ChatValidationError(str(exc)) from exc
    if switch_intent is not None:
        return post_workspace_switch_message(
            source_workspace_id=workspace_id,
            target_workspace_id=switch_intent.target_workspace_id,
            display_name=switch_intent.display_name,
            content=content,
            thread_id=thread_id,
            created_at=created_at,
            run_id=None,
            agent_content=build_workspace_switch_reply(switch_intent),
            ui_action=workspace_switch_ui_action(switch_intent),
            resolve_thread=_resolve_chat_thread,
            new_message_id=_new_message_id,
        )

    # Resolve the thread early so "show me the images" can re-embed known
    # :::image blocks without launching another Lane B agent run.
    early_thread, thread_id = _resolve_chat_thread(
        workspace_id=workspace_id,
        thread_id=thread_id,
        thread_kind="ide",
        run_id=run_id,
        created_at=created_at,
    )
    redisplay_reply = maybe_generated_image_redisplay_reply(
        content,
        workspace_id=workspace_id,
        thread_id=thread_id,
    )
    if redisplay_reply:
        return post_image_redisplay_message(
            workspace_id=workspace_id,
            content=content,
            thread_id=thread_id,
            run_id=early_thread.get("run_id") or run_id or "",
            created_at=created_at,
            redisplay_reply=redisplay_reply,
            resolve_thread=_resolve_chat_thread,
            new_message_id=_new_message_id,
        )

    memory_appendix = _compose_lane_b_memory_appendix(
        thread_id=thread_id,
        content=content,
        kairo_session_id=kairo_session_id,
        composer_mode=composer_mode,
    )
    recent_turns = [
        {
            "role": str(item.get("role") or ""),
            "content": str(item.get("content") or ""),
        }
        for item in chat_store.list_thread_messages(thread_id)
    ]
    persona_reply = (
        build_lane_b_persona_reply(
            content=content,
            recent_turns=recent_turns,
            session_id=f"ide-thread:{thread_id}",
        )
        if composer_mode == "agent"
        else None
    )
    if persona_reply:
        return post_lane_b_persona_message(
            workspace_id=workspace_id,
            content=content,
            thread_id=thread_id,
            created_at=created_at,
            save_message=chat_store.save_message,
            new_message_id=_new_message_id,
            bind_attachments=lambda message_id: _bind_message_attachments(
                attachment_ids=attachment_ids,
                workspace_id=workspace_id,
                message_id=message_id,
                thread_id=thread_id,
            )[0],
            agent_content=persona_reply,
        )

    context = LaneBContext(
        workspace_id=workspace_id,
        composer_mode=composer_mode,
        active_file_path=active_file_path,
        editor_selection=editor_selection,
        terminal_snippet=terminal_snippet,
        memory_appendix=memory_appendix,
    )
    dispatch_run_id = ""
    dispatched = False
    run_record = None
    agent_terminal_session = None

    if composer_mode == "agent":
        run_record = resolve_lane_b_agent_run(
            workspace_id=workspace_id,
            content=content,
            linked_run_id=run_id,
            execution_access=execution_access,
        )
        dispatch_run_id = str(run_record["run_id"])
        agent_terminal_session = ensure_agent_session(
            workspace_id=workspace_id,
            run_id=dispatch_run_id,
        )

    if _lane_b_streaming_enabled():
        thread, thread_id = _resolve_chat_thread(
            workspace_id=workspace_id,
            thread_id=thread_id,
            thread_kind="ide",
            run_id=dispatch_run_id or None,
            created_at=created_at,
        )

        operator_message = chat_store.save_message(
            {
                "message_id": _new_message_id("message_operator"),
                "thread_id": thread_id,
                "workspace_id": workspace_id,
                "run_id": dispatch_run_id or thread.get("run_id"),
                "role": "operator",
                "content": content,
                "created_at": created_at,
            }
        )
        operator_attachments, image_paths = _bind_message_attachments(
            attachment_ids=attachment_ids,
            workspace_id=workspace_id,
            message_id=str(operator_message["message_id"]),
            thread_id=thread_id,
        )
        if operator_attachments:
            operator_message = {**operator_message, "attachments": operator_attachments}
        context = LaneBContext(
            workspace_id=workspace_id,
            composer_mode=composer_mode,
            active_file_path=active_file_path,
            editor_selection=editor_selection,
            terminal_snippet=terminal_snippet,
            image_paths=image_paths,
            memory_appendix=memory_appendix,
        )
        system_message_id = _new_message_id("message_system")
        system_message = chat_store.save_message(
            {
                "message_id": system_message_id,
                "thread_id": thread_id,
                "workspace_id": workspace_id,
                "run_id": dispatch_run_id or thread.get("run_id"),
                "role": "system",
                "content": _lane_b_system_content(
                    composer_mode=composer_mode,
                    dispatch_run_id=dispatch_run_id,
                    dispatched=False,
                    streaming=True,
                ),
                "created_at": created_at,
            }
        )
        agent_message_id = _new_message_id("message_agent")
        agent_message = chat_store.save_message(
            {
                "message_id": agent_message_id,
                "thread_id": thread_id,
                "workspace_id": workspace_id,
                "run_id": dispatch_run_id or thread.get("run_id"),
                "role": "agent",
                "content": "",
                "created_at": created_at,
            }
        )
        stream_job = LaneBStreamJob(
            thread_id=thread_id,
            agent_message_id=agent_message_id,
            system_message_id=system_message_id,
            workspace_id=workspace_id,
            content=content,
            composer_mode=composer_mode,
            active_file_path=active_file_path,
            editor_selection=editor_selection,
            terminal_snippet=terminal_snippet,
            image_paths=image_paths,
            runtime_target=runtime_target,
            runtime_model=runtime_model,
            execution_access=execution_access,
            dispatch_run_id=dispatch_run_id,
            created_at=created_at,
            memory_appendix=memory_appendix,
            kairo_session_id=kairo_session_id,
        )
        payload: dict[str, object] = {
            "thread_id": thread_id,
            "messages": [operator_message, system_message, agent_message],
            "run_id": dispatch_run_id or thread.get("run_id") or "",
            "dispatched": False,
            "run": run_record,
            "streaming": True,
            "stream_agent_message_id": agent_message_id,
            "_stream_job": stream_job,
        }
        if agent_terminal_session is not None:
            payload["agent_terminal_session"] = serialize_session(agent_terminal_session)
        return payload

    image_paths = _attachment_paths_for_ids(attachment_ids, workspace_id)
    context = LaneBContext(
        workspace_id=workspace_id,
        composer_mode=composer_mode,
        active_file_path=active_file_path,
        editor_selection=editor_selection,
        terminal_snippet=terminal_snippet,
        image_paths=image_paths,
        memory_appendix=memory_appendix,
    )
    system_content = _lane_b_system_content(
        composer_mode=composer_mode,
        dispatch_run_id="",
        dispatched=False,
    )
    lane_b_result: dict[str, object]

    if composer_mode == "agent" and run_record is not None:
        lane_b_result = generate_lane_b_result(
            context=context,
            user_prompt=content,
            run_id=dispatch_run_id,
            runtime_target=runtime_target,
            runtime_model=runtime_model,
            execution_access=execution_access,
        )
    else:
        lane_b_result = generate_lane_b_result(
            context=context,
            user_prompt=content,
            runtime_target=runtime_target,
            runtime_model=runtime_model,
            execution_access=execution_access,
        )

    agent_content = str(lane_b_result.get("content") or "")

    if composer_mode == "agent" and run_record is not None:
        dispatched, run_record = _finalize_lane_b_agent_run(
            dispatch_run_id=dispatch_run_id,
            lane_b_result=lane_b_result,
        )
        system_content = _lane_b_system_content(
            composer_mode=composer_mode,
            dispatch_run_id=dispatch_run_id,
            dispatched=dispatched,
            run_phase=str(run_record["phase"]) if run_record is not None else None,
        )

    thread, thread_id = _resolve_chat_thread(
        workspace_id=workspace_id,
        thread_id=thread_id,
        thread_kind="ide",
        run_id=dispatch_run_id or None,
        created_at=created_at,
    )

    operator_message = chat_store.save_message(
        {
            "message_id": _new_message_id("message_operator"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": dispatch_run_id or thread.get("run_id"),
            "role": "operator",
            "content": content,
            "created_at": created_at,
        }
    )
    operator_attachments, _ = _bind_message_attachments(
        attachment_ids=attachment_ids,
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
            "run_id": dispatch_run_id or thread.get("run_id"),
            "role": "system",
            "content": system_content,
            "created_at": created_at,
        }
    )
    agent_message = chat_store.save_message(
        {
            "message_id": _new_message_id("message_agent"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": dispatch_run_id or thread.get("run_id"),
            "role": "agent",
            "content": agent_content,
            "created_at": created_at,
        }
    )
    agent_attachments = bind_agent_generated_images(
        workspace_id=workspace_id,
        message_id=str(agent_message["message_id"]),
        thread_id=thread_id,
        lane_b_result=lane_b_result,
        agent_content=agent_content,
        created_at=created_at,
    )
    if agent_attachments:
        agent_message = {**agent_message, "attachments": agent_attachments}

    _remember_lane_b_turn(
        kairo_session_id=kairo_session_id,
        operator_content=content,
        agent_content=agent_content,
    )

    ui_action = lane_b_open_file_ui_action(
        operator_content=content,
        workspace_id=workspace_id,
        thread_id=thread_id,
        lane_b_result=lane_b_result,
        agent_content=agent_content,
    )

    return {
        "thread_id": thread_id,
        "messages": [operator_message, system_message, agent_message],
        "run_id": dispatch_run_id or thread.get("run_id") or "",
        "dispatched": dispatched,
        "run": run_record,
        "streaming": False,
        **(
            {"agent_terminal_session": serialize_session(agent_terminal_session)}
            if agent_terminal_session is not None
            else {}
        ),
        **({"ui_action": ui_action} if ui_action else {}),
    }


def get_chat_thread(thread_id: str) -> dict[str, object]:
    thread = chat_store.get_thread(thread_id)
    if thread is None:
        raise chat_store.ChatThreadNotFoundError(f"thread not found: {thread_id}")
    return thread


def get_chat_thread_history(thread_id: str) -> dict[str, object]:
    from app.cli_runtime.research_stream_blocks import normalize_transcript_content

    thread = chat_store.get_thread(thread_id)
    if thread is None:
        raise chat_store.ChatThreadNotFoundError(f"thread not found: {thread_id}")

    items = chat_store.list_thread_messages(thread_id)
    normalized_items: list[dict[str, object]] = []
    for item in items:
        record = dict(item)
        if record.get("role") == "agent":
            content = str(record.get("content") or "")
            if content.strip():
                record["content"] = normalize_transcript_content(content)
        normalized_items.append(record)
    enriched_items = _enrich_message_records(normalized_items)
    return {
        "thread_id": thread["thread_id"],
        "workspace_id": thread["workspace_id"],
        "run_id": thread["run_id"],
        "items": enriched_items,
        "count": len(enriched_items),
    }


def list_workspace_chat_threads(
    workspace_id: str,
    *,
    thread_kind: str = "ide",
    limit: int = 25,
) -> dict[str, object]:
    get_workspace_record(workspace_id)
    kind = _normalize_thread_kind(thread_kind)
    threads = chat_store.list_threads_for_workspace(
        workspace_id,
        thread_kind=kind,
        limit=limit,
    )
    items = [
        {
            **thread,
            "preview_label": chat_store.first_operator_message_preview(str(thread["thread_id"])),
        }
        for thread in threads
    ]
    return {
        "workspace_id": workspace_id,
        "thread_kind": kind,
        "items": items,
        "count": len(items),
    }


def create_workspace_chat_thread(
    workspace_id: str,
    *,
    thread_kind: str = "ide",
    run_id: str | None = None,
) -> dict[str, object]:
    get_workspace_record(workspace_id)
    kind = _normalize_thread_kind(thread_kind)
    created_at = _utc_now()
    created = chat_store.create_thread(
        workspace_id=workspace_id,
        run_id=run_id,
        created_at=created_at,
        thread_kind=kind,
    )
    return {
        **created,
        "preview_label": "New chat",
    }


def get_workspace_chat_thread(
    workspace_id: str,
    *,
    thread_kind: str = "operator",
) -> dict[str, object]:
    get_workspace_record(workspace_id)
    kind = _normalize_thread_kind(thread_kind)
    thread = chat_store.get_latest_thread_for_workspace(workspace_id, thread_kind=kind)
    if thread is None:
        return {
            "thread_id": None,
            "workspace_id": workspace_id,
            "run_id": None,
            "thread_kind": kind,
            "updated_at": None,
        }

    return {
        "thread_id": thread["thread_id"],
        "workspace_id": thread["workspace_id"],
        "run_id": thread["run_id"],
        "thread_kind": thread.get("thread_kind", kind),
        "updated_at": thread["updated_at"],
    }
