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


def _run_mode_for_composer(composer_mode: str | None) -> str:
    normalized = str(composer_mode or "agent").strip().lower()
    if normalized == "debug":
        return "debug"
    if normalized == "plan":
        return "plan"
    return "agent"


def resolve_lane_b_agent_run(
    *,
    workspace_id: str,
    content: str,
    linked_run_id: str | None,
    execution_access: str | None,
    composer_mode: str | None = None,
    employee_role: str | None = None,
) -> dict[str, object]:
    run_mode = _run_mode_for_composer(composer_mode)
    cleaned_role = str(employee_role or "").strip().lower() or None
    if linked_run_id:
        try:
            existing = get_run(linked_run_id)
        except RunNotFoundError:
            existing = None
        if existing is not None and str(existing.get("workspace_id") or "") == workspace_id:
            existing_mode = str(existing.get("mode") or "agent").strip().lower()
            # Switching Agent ↔ Debug must start a fresh run, not resume the other mode.
            if existing_mode == run_mode:
                # Backfill role onto employee IDE runs that were created before tagging.
                if cleaned_role and not str(existing.get("employee_role") or "").strip():
                    existing["employee_role"] = cleaned_role
                    from app.persistence import run_store

                    existing = run_store.save_run(existing)
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

    detail = (
        "Lane B debug-mode evidence loop"
        if run_mode == "debug"
        else "Lane B plan-mode planning request"
        if run_mode == "plan"
        else "Lane B agent-mode runtime request"
    )
    return create_run(
        workspace_id=workspace_id,
        mode=run_mode,
        summary=lane_b_run_summary(content),
        detail=detail,
        employee_role=cleaned_role,
        # A direct employee-composer message is a new operator-directed turn.
        # Open fleet tasks are leased only by the Task Board/scheduler, where
        # the exact task/run linkage is explicit. Automatically attaching an
        # unrelated queued verification task here made arbitrary questions
        # inherit stale acceptance criteria and fail the wrong Gate 6 path.
        task_id=None,
        requires_approval=(
            False if run_mode == "plan" else lane_b_agent_requires_approval(execution_access)
        ),
    )
