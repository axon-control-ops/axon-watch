"""Bounded post-dispatch orchestration for operator chat commands."""

from __future__ import annotations

from typing import Any

from app.chat.command_executor import CommandExecutionResult, execute_command
from app.runs.service import RunLifecycleError, append_run_execution_receipt, mark_review_ready


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
