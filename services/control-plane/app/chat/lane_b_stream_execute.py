"""Lane B streaming job execution for IDE composer replies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.chat.lane_b_agent import EditorSelectionContext, LaneBContext, generate_lane_b_result
from app.chat.lane_b_generated_image_actions import (
    bind_agent_generated_images,
    lane_b_open_file_ui_action,
)
from app.chat.lane_b_plan_run import finalize_lane_b_plan_run
from app.chat.reply_verification import verify_lane_b_reply
from app.cli_runtime.approval_gate import is_run_linked_composer_mode, is_tool_capable_composer_mode
from app.cli_runtime.research_stream_blocks import normalize_transcript_content
from app.chat.progress_milestones import (
    persist_stream_delta,
    publish_completion_milestone,
    publish_stream_error_milestone,
)
from app.plans.service import maybe_attach_plan_artifact
from app.chat.stream_hub import close_chat_stream, clear_chat_stream_buffer, publish_chat_stream_event
from app.kairo.turn_memory import remember_turn
from app.persistence import chat_store
from app.runs.service import (
    RunLifecycleError,
    RunNotFoundError,
    append_run_execution_receipt,
    complete_run,
    fail_run,
    get_run,
)
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root
from app.workspace_agents.critical_review_clause import (
    MISSING_CONFIDENCE_DETAIL,
    parse_confidence,
)


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


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def remember_lane_b_turn(
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


def lane_b_system_content(
    *,
    composer_mode: str,
    dispatch_run_id: str,
    dispatched: bool,
    run_phase: str | None = None,
    streaming: bool = False,
) -> str:
    if streaming:
        if is_tool_capable_composer_mode(composer_mode) and dispatch_run_id:
            return f"Lane B ({composer_mode}) — streaming runtime reply for run {dispatch_run_id}."
        if str(composer_mode or "").strip().lower() == "plan" and dispatch_run_id:
            return f"Lane B (plan) — streaming plan for run {dispatch_run_id}."
        return f"Lane B ({composer_mode}) — generating reply…"

    if is_tool_capable_composer_mode(composer_mode) and dispatch_run_id:
        if run_phase == "awaiting_approval":
            if dispatched:
                return (
                    f"Lane B ({composer_mode}) recorded run {dispatch_run_id} at the approval boundary. "
                    "Consultative runtime reply only; approve the run before tool execution."
                )
            return (
                f"Lane B ({composer_mode}) recorded run {dispatch_run_id} at the approval boundary. "
                "Approve the run before tool execution starts."
            )
        if dispatched:
            return (
                f"Lane B ({composer_mode}) dispatched to runtime fabric for run {dispatch_run_id} "
                f"(phase {run_phase or 'executing'})."
            )
        return (
            f"Lane B ({composer_mode}) recorded run {dispatch_run_id}, but runtime dispatch fell back "
            f"to a consultative reply (phase {run_phase or 'executing'})."
        )
    if str(composer_mode or "").strip().lower() == "plan" and dispatch_run_id:
        phase = run_phase or "executing"
        if dispatched:
            return (
                f"Lane B (plan) recorded run {dispatch_run_id} "
                f"(phase {phase})."
            )
        return (
            f"Lane B (plan) recorded run {dispatch_run_id}, but plan generation fell back "
            f"(phase {phase})."
        )
    return f"Lane B ({composer_mode}) — conversational reply only; no command dispatch."


def finalize_lane_b_agent_run(
    *,
    dispatch_run_id: str,
    lane_b_result: dict[str, object],
    reply_text: str = "",
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
    try:
        if dispatched:
            confidence = parse_confidence(reply_text)
            if confidence is None:
                run_record = append_run_execution_receipt(
                    dispatch_run_id,
                    receipt_type="critical_review",
                    receipt_summary=MISSING_CONFIDENCE_DETAIL,
                    actor="critical_review",
                    success=False,
                    intent="lane_b_agent",
                )
                run_record = fail_run(
                    dispatch_run_id,
                    receipt_summary=MISSING_CONFIDENCE_DETAIL,
                )
                return False, run_record
            run_record = append_run_execution_receipt(
                dispatch_run_id,
                receipt_type="critical_review",
                receipt_summary=f"Critical Review Confidence: {confidence}/10",
                actor="critical_review",
                success=True,
                intent="lane_b_agent",
            )
            run_record = complete_run(dispatch_run_id)
        else:
            run_record = fail_run(
                dispatch_run_id,
                receipt_summary=receipt_summary,
            )
    except RunLifecycleError as exc:
        try:
            run_record = fail_run(
                dispatch_run_id,
                receipt_summary=f"Lane B finalization failed: {exc}",
            )
        except RunLifecycleError:
            run_record = append_run_execution_receipt(
                dispatch_run_id,
                receipt_type="finalization_error",
                receipt_summary=str(exc),
                actor="cli_runtime",
                success=False,
                intent="lane_b_agent",
            )
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
            user_prompt=job.content,
        )
        agent_content = normalize_transcript_content(agent_content)
        updated_at = _utc_now()
        plan_meta: dict[str, object] | None = None
        agent_content, plan_meta = maybe_attach_plan_artifact(
            composer_mode=job.composer_mode,
            workspace_id=job.workspace_id,
            thread_id=job.thread_id,
            source_message_id=job.agent_message_id,
            agent_content=agent_content,
            created_at=updated_at,
        )
        chat_store.update_message_content(
            message_id=job.agent_message_id,
            content=agent_content,
            updated_at=updated_at,
        )
        remember_lane_b_turn(
            kairo_session_id=job.kairo_session_id,
            operator_content=job.content,
            agent_content=agent_content,
        )

        if is_tool_capable_composer_mode(job.composer_mode) and job.dispatch_run_id:
            dispatched, run_record = finalize_lane_b_agent_run(
                dispatch_run_id=job.dispatch_run_id,
                lane_b_result=lane_b_result,
                reply_text=agent_content,
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
            system_content = lane_b_system_content(
                composer_mode=job.composer_mode,
                dispatch_run_id=job.dispatch_run_id,
                dispatched=dispatched,
                run_phase=str(run_record["phase"]) if run_record is not None else None,
            )
        elif (
            str(job.composer_mode or "").strip().lower() == "plan"
            and job.dispatch_run_id
        ):
            # Plan is run-linked but not tool-capable; still finalize to review_ready.
            dispatched, run_record = finalize_lane_b_plan_run(
                run_id=job.dispatch_run_id,
                lane_b_result=lane_b_result,
                reply_text=agent_content,
            )
            system_content = lane_b_system_content(
                composer_mode=job.composer_mode,
                dispatch_run_id=job.dispatch_run_id,
                dispatched=dispatched,
                run_phase=str(run_record["phase"]) if run_record is not None else None,
            )
        else:
            system_content = lane_b_system_content(
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
                **({"plan": plan_meta} if plan_meta else {}),
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
        if is_run_linked_composer_mode(job.composer_mode) and job.dispatch_run_id:
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
