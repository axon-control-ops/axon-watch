"""Resolve whether an operator command attaches to a run or dispatches a new one."""

from __future__ import annotations

from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import run_store
from app.runs.service import create_run

ATTACH_COMMAND_PHASES = {
    "queued",
    "starting",
    "planning",
    "executing",
    "waiting_external",
    "awaiting_input",
    "paused",
}


def summarize_command_for_run(content: str, *, max_length: int = 120) -> str:
    trimmed = content.strip()
    if len(trimmed) <= max_length:
        return trimmed
    return f"{trimmed[: max_length - 3].rstrip()}..."


def build_command_dispatch_ack(
    *,
    run_id: str,
    phase: str,
    dispatched: bool,
) -> str:
    if dispatched:
        return f"Run {run_id} dispatched · phase {phase}"
    return f"Command linked to run {run_id} · phase {phase}"


def resolve_command_dispatch(
    *,
    workspace_id: str,
    content: str,
    run_id: str | None,
) -> tuple[str, dict[str, Any], bool]:
    if run_id:
        existing = run_store.get_run(run_id)
        if (
            existing is not None
            and existing["workspace_id"] == workspace_id
            and existing["phase"] in ATTACH_COMMAND_PHASES
            and not is_terminal_phase(existing["phase"])
        ):
            return run_id, existing, False

    summary = summarize_command_for_run(content)
    record = create_run(
        workspace_id=workspace_id,
        mode="agent",
        summary=summary,
        detail=f"Operator command: {content.strip()}",
    )
    return record["run_id"], record, True
