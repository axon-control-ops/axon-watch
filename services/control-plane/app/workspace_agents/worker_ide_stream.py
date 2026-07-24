"""Mirror continuous-worker Lane B transcripts into specialist IDE threads."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.chat.lane_b_stream_execute import lane_b_system_content
from app.chat.progress_milestones import (
    persist_stream_delta,
    publish_completion_milestone,
    publish_stream_error_milestone,
)
from app.chat.stream_hub import clear_chat_stream_buffer, close_chat_stream, publish_chat_stream_event
from app.cli_runtime.research_stream_blocks import normalize_transcript_content
from app.persistence import chat_store
from app.workspace_agents import build_company_roster
from app.workspace_agents.config_loader import EmployeeConfig

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class WorkerIdeStream:
    thread_id: str
    agent_message_id: str
    system_message_id: str
    employee_id: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _new_message_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def resolve_worker_employee_id(workspace_id: str, employee: EmployeeConfig) -> str | None:
    cleaned = str(employee.employee_id or "").strip()
    if cleaned:
        return cleaned
    company = build_company_roster(workspace_id)
    rows = company.get("employees") if isinstance(company, dict) else None
    if not isinstance(rows, list):
        return None
    want = str(employee.role or "").strip().lower()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("role") or "").strip().lower() != want:
            continue
        employee_id = str(row.get("employee_id") or "").strip()
        if employee_id:
            return employee_id
    return None


def _task_goal_preview(task: dict[str, Any] | None) -> str:
    if not isinstance(task, dict):
        return "(no task goal)"
    goal = " ".join(str(task.get("goal") or "").split())
    if not goal:
        return "(no task goal)"
    if len(goal) > 400:
        return f"{goal[:399].rstrip()}…"
    return goal


def prepare_worker_ide_stream(
    *,
    workspace_id: str,
    employee: EmployeeConfig,
    run_id: str,
    task_id: str,
    task: dict[str, Any] | None,
) -> WorkerIdeStream | None:
    """Bind the employee IDE thread and seed streaming placeholders for this shift."""
    employee_id = resolve_worker_employee_id(workspace_id, employee)
    if not employee_id:
        logger.warning(
            "prepare_worker_ide_stream: no employee_id for workspace=%s role=%s name=%s run=%s",
            workspace_id,
            employee.role,
            employee.name,
            run_id,
        )
        return None

    created_at = _utc_now()
    thread = chat_store.find_thread_for_employee(
        workspace_id,
        employee_id=employee_id,
        thread_kind="ide",
    )
    display_name = str(employee.name or "").strip() or employee.role.replace("_", " ").title()
    if thread is None:
        thread = chat_store.create_thread(
            workspace_id=workspace_id,
            run_id=run_id,
            created_at=created_at,
            thread_kind="ide",
            title=f"{display_name} · worker",
            employee_id=employee_id,
            employee_role=employee.role,
        )
    thread_id = str(thread["thread_id"])
    clear_chat_stream_buffer(thread_id)

    chat_store.save_message(
        {
            "message_id": _new_message_id("message_operator"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": run_id,
            "role": "operator",
            "content": (
                f"Continuous worker dispatch started.\n"
                f"Role: {employee.role}\n"
                f"Task: {task_id}\n"
                f"Run: {run_id}\n"
                f"Goal: {_task_goal_preview(task)}"
            ),
            "created_at": created_at,
        }
    )
    system_message_id = _new_message_id("message_system")
    chat_store.save_message(
        {
            "message_id": system_message_id,
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": run_id,
            "role": "system",
            "content": lane_b_system_content(
                composer_mode="agent",
                dispatch_run_id=run_id,
                dispatched=False,
                streaming=True,
            ),
            "created_at": created_at,
        }
    )
    agent_message_id = _new_message_id("message_agent")
    chat_store.save_message(
        {
            "message_id": agent_message_id,
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": run_id,
            "role": "agent",
            "content": "",
            "created_at": created_at,
        }
    )
    publish_chat_stream_event(
        thread_id,
        {
            "type": "chat_stream_started",
            "thread_id": thread_id,
            "message_id": agent_message_id,
            "run_id": run_id,
            "source": "continuous_worker",
        },
    )
    return WorkerIdeStream(
        thread_id=thread_id,
        agent_message_id=agent_message_id,
        system_message_id=system_message_id,
        employee_id=employee_id,
    )


def stream_worker_chunk(
    stream: WorkerIdeStream,
    *,
    previous_content: str,
    accumulated: str,
    delta: str,
) -> str:
    return persist_stream_delta(
        thread_id=stream.thread_id,
        message_id=stream.agent_message_id,
        previous_content=previous_content,
        accumulated=accumulated,
        delta=delta,
        updated_at=_utc_now(),
    )


def finalize_worker_ide_stream(
    stream: WorkerIdeStream,
    *,
    reply_text: str,
    dispatched: bool,
    run_record: dict[str, Any] | None,
) -> None:
    updated_at = _utc_now()
    agent_content = normalize_transcript_content(str(reply_text or ""))
    chat_store.update_message_content(
        message_id=stream.agent_message_id,
        content=agent_content,
        updated_at=updated_at,
    )
    run_phase = str((run_record or {}).get("phase") or "").strip().lower() or None
    run_id = str((run_record or {}).get("run_id") or "").strip()
    system_content = lane_b_system_content(
        composer_mode="agent",
        dispatch_run_id=run_id,
        dispatched=dispatched,
        run_phase=run_phase,
    )
    chat_store.update_message_content(
        message_id=stream.system_message_id,
        content=system_content,
        updated_at=updated_at,
    )
    publish_completion_milestone(
        thread_id=stream.thread_id,
        message_id=stream.agent_message_id,
        verification_warnings=[],
        run_record=run_record,
    )
    publish_chat_stream_event(
        stream.thread_id,
        {
            "type": "chat_stream_done",
            "thread_id": stream.thread_id,
            "message_id": stream.agent_message_id,
            "content": agent_content,
            "system_message_id": stream.system_message_id,
            "system_content": system_content,
            "dispatched": dispatched,
            "run_id": run_id,
            "run": run_record,
            "source": "continuous_worker",
        },
    )
    close_chat_stream(stream.thread_id)
    clear_chat_stream_buffer(stream.thread_id)


def fail_worker_ide_stream(stream: WorkerIdeStream, *, error: str, run_id: str) -> None:
    fallback = str(error or "").strip() or "continuous worker dispatch failed"
    updated_at = _utc_now()
    chat_store.update_message_content(
        message_id=stream.agent_message_id,
        content=fallback,
        updated_at=updated_at,
    )
    chat_store.update_message_content(
        message_id=stream.system_message_id,
        content=(
            f"Lane B (agent) continuous worker failed for run {run_id}: {fallback}"
        ),
        updated_at=updated_at,
    )
    publish_stream_error_milestone(
        thread_id=stream.thread_id,
        message_id=stream.agent_message_id,
        error=fallback,
    )
    publish_chat_stream_event(
        stream.thread_id,
        {
            "type": "chat_stream_error",
            "thread_id": stream.thread_id,
            "message_id": stream.agent_message_id,
            "content": fallback,
            "error": fallback,
            "run_id": run_id,
            "source": "continuous_worker",
        },
    )
    close_chat_stream(stream.thread_id)
    clear_chat_stream_buffer(stream.thread_id)
