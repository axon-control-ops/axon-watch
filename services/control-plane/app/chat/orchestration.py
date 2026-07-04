"""Bounded post-dispatch orchestration for operator chat commands."""

from __future__ import annotations

from typing import Any

from app.runs.service import RunLifecycleError, mark_review_ready


def build_agent_command_reply(
    *,
    content: str,
    run_record: dict[str, Any],
    dispatched: bool,
) -> str:
    run_id = str(run_record["run_id"])
    phase = str(run_record["phase"])
    summary = str(run_record.get("summary") or content.strip())

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
    run_record: dict[str, Any],
    dispatched: bool,
) -> dict[str, Any]:
    if not dispatched or run_record["phase"] != "executing":
        return run_record

    try:
        return mark_review_ready(str(run_record["run_id"]))
    except RunLifecycleError:
        return run_record
