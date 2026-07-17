"""Lifecycle finalization for linked Lane B Plan runs."""

from __future__ import annotations

from app.runs.service import (
    RunLifecycleError,
    append_run_execution_receipt,
    fail_run,
    mark_review_ready,
)


def finalize_lane_b_plan_run(
    *,
    run_id: str,
    lane_b_result: dict[str, object],
) -> tuple[bool, dict[str, object] | None]:
    """Record the planning result and leave successful plans ready for review."""

    dispatched = bool(lane_b_result.get("dispatched"))
    runtime_label = str(lane_b_result.get("runtime_label") or "runtime fallback")
    reason = str(lane_b_result.get("reason") or "").strip()
    receipt_summary = (
        f"Lane B plan generated via {runtime_label}"
        if dispatched
        else f"Lane B plan fallback failed ({reason or 'runtime unavailable'})"
    )
    run_record = append_run_execution_receipt(
        run_id,
        receipt_type="plan_generation",
        receipt_summary=receipt_summary,
        actor="cli_runtime",
        success=dispatched,
        intent="lane_b_plan",
    )
    try:
        if dispatched:
            run_record = mark_review_ready(run_id)
        else:
            run_record = fail_run(run_id, receipt_summary=receipt_summary)
    except RunLifecycleError:
        try:
            run_record = fail_run(
                run_id,
                receipt_summary="Lane B plan finalization failed",
            )
        except RunLifecycleError:
            return dispatched, run_record
    return dispatched, run_record
