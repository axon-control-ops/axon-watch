"""Lane B streaming job execution for IDE composer replies."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.chat.lane_b_agent import EditorSelectionContext, LaneBContext, generate_lane_b_result
from app.chat.lane_b_generated_image_actions import (
    bind_agent_generated_images,
    lane_b_open_file_ui_action,
)
from app.chat.chat_stream_defer import finish_chat_stream
from app.chat.lane_b_stream_progress import build_lane_b_stream_on_chunk
from app.chat.direct_reply_acceptance import enforce_direct_reply_acceptance
from app.chat.lane_b_turn_memory import remember_lane_b_turn
from app.chat.reply_verification import verify_lane_b_reply
from app.cli_runtime.approval_gate import is_tool_capable_composer_mode
from app.cli_runtime.research_stream_blocks import normalize_transcript_content
from app.chat.progress_milestones import (
    publish_completion_milestone,
    publish_stream_error_milestone,
)
from app.plans.service import maybe_attach_plan_artifact
from app.persistence import chat_store
from app.workspace_agents.execution_policy import AgentExecutionPolicy
from app.runs.service import (
    RunLifecycleError,
    RunNotFoundError,
    append_run_execution_receipt,
    complete_run,
    fail_run,
    get_run,
)
from app.terminal.active_chat_stream import (
    clear_active_chat_stream,
    register_active_chat_stream,
)
from app.terminal.agent_job_chat import merge_active_agent_job_terminals
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root
from app.workspace_agents.critical_review_clause import (
    MISSING_CONFIDENCE_DETAIL,
    critical_review_receipt_summary,
    resolve_critical_review_confidence,
)
from app.workspace_agents.employee_first_person import (
    employee_name_from_persona_block,
    rewrite_employee_third_person_to_first,
)

logger = logging.getLogger(__name__)


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
    workspace_root: Path | None = None
    # Role baseline for the thread this turn is dispatched under — independent
    # of the operator's own execution_access toggle above; see
    # try_lane_b_git_commit_dispatch for why both are needed.
    execution_policy: AgentExecutionPolicy | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
    return f"Lane B ({composer_mode}) — conversational reply only; no command dispatch."


def finalize_lane_b_agent_run(
    *,
    dispatch_run_id: str,
    lane_b_result: dict[str, object],
    reply_text: str = "",
    workspace_root: str | None = None,
    defer_complete: bool = False,
    require_critical_review: bool = True,
) -> tuple[bool, dict[str, object] | None]:
    """Finalize a Lane B agent run.

    When ``defer_complete`` is True (scheduled workers), critical review and
    Gate 6 acceptance still run, but ``complete_run`` is left to the caller so
    workspace delivery can publish before the terminal phase.

    ``require_critical_review`` (default True, preserving prior behavior for
    every existing caller) gates whether a missing "Confidence: N/10" line
    fails the run. Routine (non-review-type) continuous shifts pass False —
    see is_review_type_task() — so an ordinary reply is not hard-failed for
    omitting a ritual it was never asked to perform.
    """
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
            _maybe_route_terminal_capability_lane_b(
                dispatch_run_id=dispatch_run_id,
                run_record=run_record,
                reply_text=reply_text,
            )
            accepted, acceptance_record = enforce_direct_reply_acceptance(
                dispatch_run_id, reply_text
            )
            run_record = acceptance_record or run_record
            if not accepted:
                _maybe_notify_lead_after_lane_b(
                    dispatch_run_id=dispatch_run_id,
                    run_record=run_record,
                    reply_text=reply_text,
                )
                return False, run_record
            confidence, auto_recovered = resolve_critical_review_confidence(reply_text)
            if confidence is None:
                if require_critical_review:
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
                    # Still notify Lead/VAXON on terminal failure so the chain is not silent.
                    _maybe_notify_lead_after_lane_b(
                        dispatch_run_id=dispatch_run_id,
                        run_record=run_record,
                        reply_text=reply_text,
                    )
                    return False, run_record
                # Routine reply, ritual not required — proceed without demanding
                # a confidence line or stamping an unrequested receipt for it.
            else:
                run_record = append_run_execution_receipt(
                    dispatch_run_id,
                    receipt_type="critical_review",
                    receipt_summary=critical_review_receipt_summary(
                        confidence, auto_recovered=auto_recovered
                    ),
                    actor="critical_review",
                    success=True,
                    intent="lane_b_agent",
                )
            from app.workspace_agents.verifier_contract import (
                ensure_acceptance_before_publish,
            )

            ensure_acceptance_before_publish(
                dispatch_run_id,
                workspace_root=workspace_root,
            )
            if defer_complete:
                append_run_execution_receipt(
                    dispatch_run_id,
                    receipt_type="worker_delivery",
                    receipt_summary="stage=verified · awaiting workspace delivery publish",
                    actor="workspace_delivery",
                    success=True,
                    intent="workspace_delivery",
                )
            else:
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
            dispatched = False
    _maybe_notify_lead_after_lane_b(
        dispatch_run_id=dispatch_run_id,
        run_record=run_record,
        reply_text=reply_text,
    )
    return dispatched, run_record


def _maybe_route_terminal_capability_lane_b(
    *,
    dispatch_run_id: str,
    run_record: dict[str, object] | None,
    reply_text: str,
) -> dict[str, object] | None:
    """Smart-route one-shot Lane B shifts that hit terminal limits."""
    if not isinstance(run_record, dict):
        return None
    if str(run_record.get("task_id") or "").strip():
        return None
    workspace_id = str(run_record.get("workspace_id") or "").strip()
    role = str(run_record.get("employee_role") or "").strip().lower()
    if not workspace_id or not role or role == "overview_agent":
        return None
    from app.workspace_agents.capability_routing import (
        looks_like_terminal_capability_handoff,
        try_route_capability_handoff,
    )

    if not looks_like_terminal_capability_handoff(reply_text=reply_text):
        return None
    try:
        from app.workspace_agents import build_company_roster

        name = role
        for row in build_company_roster(workspace_id).get("employees") or []:
            if str(row.get("role") or "").strip().lower() == role:
                name = str(row.get("name") or role).strip() or role
                break
    except Exception:  # noqa: BLE001
        name = role
    return try_route_capability_handoff(
        workspace_id=workspace_id,
        source_run_id=dispatch_run_id,
        source_role=role,
        source_name=name,
        reply_text=reply_text,
        goal_hint=reply_text[:280],
    )


def _maybe_notify_lead_after_lane_b(
    *,
    dispatch_run_id: str,
    run_record: dict[str, object] | None,
    reply_text: str,
) -> None:
    """Lead takeover for specialists; Lead-shift → VAXON flash when Dana finishes."""
    if not isinstance(run_record, dict):
        return
    phase = str(run_record.get("phase") or "").strip().lower()
    if phase not in {"completed", "failed"}:
        return
    role = str(run_record.get("employee_role") or "").strip().lower()
    if not role or role == "overview_agent":
        return
    # Continuous workers already notify after task ledger finalize.
    if str(run_record.get("task_id") or "").strip():
        return
    workspace_id = str(run_record.get("workspace_id") or "").strip()
    if not workspace_id:
        return
    try:
        from app.workspace_agents import build_company_roster
        from app.workspace_agents.lead_replan import notify_lead_after_worker_task
        from app.workspace_agents.lead_vaxon_handoff import notify_vaxon_after_lead_shift

        name = role
        company = build_company_roster(workspace_id)
        for row in company.get("employees") or []:
            if not isinstance(row, dict):
                continue
            if str(row.get("role") or "").strip().lower() == role:
                name = str(row.get("name") or role).strip() or role
                break
        run_id = str(run_record.get("run_id") or dispatch_run_id)
        if role == "lead":
            notify_vaxon_after_lead_shift(
                workspace_id=workspace_id,
                run_id=run_id,
                employee_name=name,
                phase=phase,
                reply_text=reply_text,
            )
            return
        notify_lead_after_worker_task(
            workspace_id=workspace_id,
            task_id="",
            run_id=run_id,
            employee_role=role,
            employee_name=name,
            phase=phase,
            reply_text=reply_text,
        )
    except Exception:  # noqa: BLE001 — never block Lane B finalize on Lead notify
        logger.exception(
            "lead/VAXON notify after Lane B shift failed for %s",
            dispatch_run_id,
        )


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
    register_active_chat_stream(
        workspace_id=job.workspace_id,
        thread_id=job.thread_id,
        message_id=job.agent_message_id,
        run_id=job.dispatch_run_id,
    )
    on_chunk, _get_milestone_content = build_lane_b_stream_on_chunk(
        thread_id=job.thread_id,
        agent_message_id=job.agent_message_id,
        dispatch_run_id=job.dispatch_run_id,
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
            workspace_root=job.workspace_root,
            execution_policy=job.execution_policy,
        )
        agent_content = str(lane_b_result.get("content") or "")
        speaker_name = employee_name_from_persona_block(job.memory_appendix)
        agent_content = rewrite_employee_third_person_to_first(agent_content, speaker_name)
        execution_tier = str(lane_b_result.get("execution_tier") or "consultative")
        # Verify edit receipts against the same checkout the runtime used.
        # Falling back to the bound project root made valid sandbox edits look
        # missing and, worse, could validate an unrelated live-tree path.
        workspace_root = job.workspace_root
        if workspace_root is None:
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
        agent_content = merge_active_agent_job_terminals(
            job.agent_message_id,
            agent_content,
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
        finish_chat_stream(
            thread_id=job.thread_id,
            message_id=job.agent_message_id,
            terminal_payload={
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
        fallback = merge_active_agent_job_terminals(job.agent_message_id, fallback)
        updated_at = _utc_now()
        chat_store.update_message_content(
            message_id=job.agent_message_id,
            content=fallback,
            updated_at=updated_at,
        )
        run_record = None
        if is_tool_capable_composer_mode(job.composer_mode) and job.dispatch_run_id:
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
        finish_chat_stream(
            thread_id=job.thread_id,
            message_id=job.agent_message_id,
            terminal_payload={
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
        clear_active_chat_stream(job.workspace_id, message_id=job.agent_message_id)
