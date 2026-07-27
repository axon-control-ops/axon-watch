"""Lane B IDE composer message posting orchestration."""

from __future__ import annotations

from app.chat.lane_b_agent import EditorSelectionContext, LaneBContext, generate_lane_b_result
from app.chat.lane_b_fast_paths import post_image_redisplay_message, post_workspace_switch_message
from app.chat.lane_b_generated_image_actions import (
    bind_agent_generated_images,
    lane_b_open_file_ui_action,
    maybe_generated_image_redisplay_reply,
)
from app.chat.lane_b_persona_fast_path import build_lane_b_persona_reply, post_lane_b_persona_message
from app.chat.lane_b_plan_run import finalize_lane_b_plan_run
from app.chat.lane_b_run_dispatch import resolve_lane_b_agent_run
from app.chat.lane_b_system_content import lane_b_system_content as _lane_b_system_content
from app.chat.workspace_switch import (
    WorkspaceSwitchError,
    build_workspace_switch_reply,
    resolve_workspace_switch_intent,
    workspace_switch_ui_action,
)
from app.cli_runtime.approval_gate import is_run_linked_composer_mode, is_tool_capable_composer_mode
from app.persistence import chat_store
from app.plans.service import maybe_attach_plan_artifact
from app.terminal.session_registry import ensure_agent_session, serialize_session
from app.workspace_agents.employee_persona_prompt import build_employee_persona_appendix


def post_lane_b_message(
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
    from app.chat.service import (
        ChatValidationError,
        LaneBStreamJob,
        _attachment_paths_for_ids,
        _bind_message_attachments,
        _compose_lane_b_memory_appendix,
        _finalize_lane_b_agent_run,
        _lane_b_streaming_enabled,
        _new_message_id,
        _remember_lane_b_turn,
        _resolve_chat_thread,
    )

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
    thread_employee_id = str(early_thread.get("employee_id") or "").strip()
    employee_persona = build_employee_persona_appendix(
        workspace_id=workspace_id,
        employee_id=thread_employee_id or None,
        employee_role=(
            str(early_thread.get("employee_role") or "").strip() or None
        ),
    )
    if employee_persona:
        memory_appendix = "\n\n".join(
            part
            for part in (employee_persona, memory_appendix)
            if part and str(part).strip()
        )
    recent_turns = [
        {
            "role": str(item.get("role") or ""),
            "content": str(item.get("content") or ""),
        }
        for item in chat_store.list_thread_messages(thread_id)
    ]
    # VAXON smalltalk fast-path stays on generic threads only — employee 1:1s dispatch.
    persona_reply = (
        build_lane_b_persona_reply(
            content=content,
            recent_turns=recent_turns,
            session_id=f"ide-thread:{thread_id}",
        )
        if composer_mode == "agent" and not thread_employee_id
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

    if is_run_linked_composer_mode(composer_mode):
        run_record = resolve_lane_b_agent_run(
            workspace_id=workspace_id,
            content=content,
            linked_run_id=run_id,
            execution_access=execution_access,
            composer_mode=composer_mode,
            employee_role=(
                str(early_thread.get("employee_role") or "").strip() or None
            ),
        )
        dispatch_run_id = str(run_record["run_id"])
        if is_tool_capable_composer_mode(composer_mode):
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

    if is_run_linked_composer_mode(composer_mode) and run_record is not None:
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
    # Thread id may still be unresolved here; capture after resolve below for plan mode.

    if is_tool_capable_composer_mode(composer_mode) and run_record is not None:
        dispatched, run_record = _finalize_lane_b_agent_run(
            dispatch_run_id=dispatch_run_id,
            lane_b_result=lane_b_result,
            reply_text=agent_content,
        )
        system_content = _lane_b_system_content(
            composer_mode=composer_mode,
            dispatch_run_id=dispatch_run_id,
            dispatched=dispatched,
            run_phase=str(run_record["phase"]) if run_record is not None else None,
        )
    elif composer_mode == "plan" and run_record is not None:
        dispatched, run_record = finalize_lane_b_plan_run(
            run_id=dispatch_run_id,
            lane_b_result=lane_b_result,
            reply_text=agent_content,
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
    agent_message_id = _new_message_id("message_agent")
    agent_content, plan_meta = maybe_attach_plan_artifact(
        composer_mode=composer_mode,
        workspace_id=workspace_id,
        thread_id=thread_id,
        source_message_id=agent_message_id,
        agent_content=agent_content,
        created_at=created_at,
    )
    agent_message = chat_store.save_message(
        {
            "message_id": agent_message_id,
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
        **({"plan": plan_meta} if plan_meta else {}),
    }
