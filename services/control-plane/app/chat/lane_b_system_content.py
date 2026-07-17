"""Operator-visible system messages for Lane B runs."""

from __future__ import annotations

from app.cli_runtime.approval_gate import is_tool_capable_composer_mode


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
        if composer_mode == "plan" and dispatch_run_id:
            return f"Lane B (plan) — streaming planning reply for run {dispatch_run_id}."
        return f"Lane B ({composer_mode}) — generating reply…"

    if composer_mode == "plan" and dispatch_run_id:
        if dispatched:
            return (
                f"Lane B (plan) generated plan {dispatch_run_id} "
                f"(phase {run_phase or 'review_ready'})."
            )
        return (
            f"Lane B (plan) recorded run {dispatch_run_id}, but planning fell back "
            f"(phase {run_phase or 'failed'})."
        )

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
