"""Bounded post-dispatch orchestration for operator chat commands."""

from __future__ import annotations

from typing import Any

from app.chat.command_executor import (
    CommandExecutionResult,
    execute_command,
    execute_resume_from_review,
)
from app.runs.service import RunLifecycleError, append_run_execution_receipt, get_run, list_runs, mark_review_ready


def build_agent_command_reply(
    *,
    content: str,
    run_record: dict[str, Any],
    dispatched: bool,
    execution: CommandExecutionResult | None = None,
) -> str:
    run_id = str(run_record["run_id"])
    phase = str(run_record["phase"])
    summary = str(run_record.get("summary") or content.strip())

    if execution is not None:
        status = "ok" if execution.success else "failed"
        if execution.intent == "resume_from_review":
            return (
                f"Executed `{execution.intent}` ({status}) for run {run_id}.\n\n"
                f"```\n{execution.output}\n```\n\n"
                f"Phase is now {phase}."
            )
        return (
            f"Executed `{execution.intent}` ({status}) for run {run_id}.\n\n"
            f"```\n{execution.output}\n```\n\n"
            f"Phase is now {phase}. Review when ready."
        )

    if dispatched:
        if phase == "review_ready":
            return (
                f"Command accepted for run {run_id}. "
                f"Execution paused for review: {summary}"
            )
        return f"Command dispatched to run {run_id} (phase {phase}): {summary}"

    return f"Command linked to active run {run_id} (phase {phase})."


def _anchor_run_for_failed_resume(
    *,
    workspace_id: str,
    execution: CommandExecutionResult,
) -> dict[str, Any]:
    if execution.run_id:
        existing = get_run(execution.run_id)
        if existing is not None:
            return existing

    workspace_runs = [record for record in list_runs() if record["workspace_id"] == workspace_id]
    if workspace_runs:
        return workspace_runs[-1]

    raise RunLifecycleError(
        f"resume from review failed and no runs exist for workspace {workspace_id}",
    )


def orchestrate_resume_from_review(
    *,
    workspace_id: str,
) -> tuple[dict[str, Any], CommandExecutionResult]:
    execution = execute_resume_from_review(workspace_id)
    if execution.success and execution.run_id:
        return get_run(execution.run_id), execution
    return _anchor_run_for_failed_resume(workspace_id=workspace_id, execution=execution), execution


def orchestrate_command_run(
    *,
    workspace_id: str,
    content: str,
    run_record: dict[str, Any],
    dispatched: bool,
) -> tuple[dict[str, Any], CommandExecutionResult | None]:
    if not dispatched or run_record["phase"] != "executing":
        return run_record, None

    execution = execute_command(workspace_id=workspace_id, content=content)
    run_id = str(run_record["run_id"])
    run_record = append_run_execution_receipt(
        run_id,
        receipt_type="command_execution",
        receipt_summary=execution.receipt_summary,
        actor="command_executor",
        success=execution.success,
        intent=execution.intent,
    )

    try:
        run_record = mark_review_ready(run_id)
    except RunLifecycleError:
        pass

    return run_record, execution
