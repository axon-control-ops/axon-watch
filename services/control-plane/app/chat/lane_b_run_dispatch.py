"""Lane B agent run resolution for IDE composer submits."""

from __future__ import annotations

from app.cli_runtime.approval_gate import full_access_requested, lane_b_agent_requires_approval
from app.domain.run_state import is_terminal_phase
from app.runs.service import (
    RunLifecycleError,
    RunNotFoundError,
    approve_run,
    create_run,
    get_run,
    resume_run,
)


def lane_b_run_summary(content: str) -> str:
    trimmed = content.strip()
    if len(trimmed) <= 96:
        return trimmed
    return f"{trimmed[:93].rstrip()}..."


def resolve_lane_b_agent_run(
    *,
    workspace_id: str,
    content: str,
    linked_run_id: str | None,
    execution_access: str | None,
) -> dict[str, object]:
    if linked_run_id:
        try:
            existing = get_run(linked_run_id)
        except RunNotFoundError:
            existing = None
        if existing is not None and str(existing.get("workspace_id") or "") == workspace_id:
            phase = str(existing.get("phase") or "")
            if phase in {"review_ready", "paused"}:
                try:
                    return resume_run(linked_run_id)
                except RunLifecycleError:
                    return existing
            elif phase == "awaiting_approval" and full_access_requested(execution_access):
                # Full Access consent already covers execution; unblock the run.
                try:
                    return approve_run(linked_run_id)
                except RunLifecycleError:
                    return existing
            elif phase in {"executing", "awaiting_approval"}:
                return existing
            elif not is_terminal_phase(phase):
                return existing

    return create_run(
        workspace_id=workspace_id,
        mode="agent",
        summary=lane_b_run_summary(content),
        detail="Lane B agent-mode runtime request",
        requires_approval=lane_b_agent_requires_approval(execution_access),
    )
