"""Real agentic narration for the "started" assignment card.

The "queued" fan-out card and other assignment-status text stay template
rendered (assignment_messages.py) — see the module docstring in
lead_fan_out.py's caller for why (synchronous, once-per-specialist, inside the
operator's live chat turn; narrating those risks stacking model latency
directly in that request). The "started" card fires once per run from the
background scheduler tick, which already tolerates multi-minute shifts, so it
can afford a real model call — this is the one v1 covers.

Fails open to the existing deterministic assignment_card() template on any
error, timeout, or unusable model response: the operator always gets a status
update even when the model call fails.
"""

from __future__ import annotations

from typing import Any, Callable

from app.workspace_agents.agent_voice_style import AGENT_VOICE_STYLE_CLAUSE
from app.workspace_agents.assignment_messages import assignment_card, readable_goal

_MAX_NARRATION_CHARS = 240


def _fallback_card(
    *,
    assignee_name: str,
    assignee_role: str,
    goal: str,
    task_id: str,
    run_id: str,
    expected_files: list[str] | None,
) -> str:
    return assignment_card(
        assignee_name=assignee_name,
        assignee_role=assignee_role,
        goal=goal,
        task_id=task_id,
        run_id=run_id,
        state="started",
        expected_files=expected_files,
    )


def narrate_worker_started(
    *,
    workspace_id: str,
    assignee_name: str,
    assignee_role: str,
    goal: str,
    task_id: str,
    run_id: str,
    expected_files: list[str] | None = None,
    dispatch_runtime: Callable[..., dict[str, Any]] | None = None,
) -> str:
    """One natural first-person sentence announcing a shift has started.

    Falls back to the deterministic assignment_card() template if the model
    call fails, times out, or returns something unusable.
    """
    fallback = _fallback_card(
        assignee_name=assignee_name,
        assignee_role=assignee_role,
        goal=goal,
        task_id=task_id,
        run_id=run_id,
        expected_files=expected_files,
    )
    if dispatch_runtime is None:
        from app.workspace_agents.teammate_route import dispatch_model_tiebreak

        dispatch_runtime = dispatch_model_tiebreak

    prompt = (
        f"You are {assignee_name}, the {assignee_role} specialist. You are starting this "
        f"task now: {readable_goal(goal)}. Write ONE short first-person sentence telling "
        "the operator you're starting this, in your own natural voice. "
        f"{AGENT_VOICE_STYLE_CLAUSE} No headers, no task IDs, no markdown, one sentence only."
    )
    try:
        payload = dispatch_runtime(
            workspace_id=workspace_id,
            composer_mode="ask",
            user_prompt=prompt,
            context_block="Announce the start of a leased task in one natural sentence.",
            execution_access="consultative",
        )
    except Exception:
        return fallback

    if not isinstance(payload, dict) or not payload.get("dispatched"):
        return fallback
    content = " ".join(str(payload.get("content") or "").split()).strip()
    if not content or len(content) > _MAX_NARRATION_CHARS:
        return fallback
    return content


__all__ = ["narrate_worker_started"]
