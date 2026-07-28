"""Lifecycle finalization for linked Lane B Plan runs."""

from __future__ import annotations

from app.runs.service import (
    RunLifecycleError,
    append_run_execution_receipt,
    fail_run,
    mark_review_ready,
)
from app.workspace_agents.critical_review_clause import (
    MISSING_CONFIDENCE_DETAIL,
    critical_review_receipt_summary,
    resolve_critical_review_confidence,
)


def finalize_lane_b_plan_run(
    *,
    run_id: str,
    lane_b_result: dict[str, object],
    reply_text: str = "",
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
            confidence, auto_recovered = resolve_critical_review_confidence(reply_text)
            if confidence is None:
                run_record = append_run_execution_receipt(
                    run_id,
                    receipt_type="critical_review",
                    receipt_summary=MISSING_CONFIDENCE_DETAIL,
                    actor="critical_review",
                    success=False,
                    intent="lane_b_plan",
                )
                run_record = fail_run(run_id, receipt_summary=MISSING_CONFIDENCE_DETAIL)
                return False, run_record
            run_record = append_run_execution_receipt(
                run_id,
                receipt_type="critical_review",
                receipt_summary=critical_review_receipt_summary(
                    confidence, auto_recovered=auto_recovered
                ),
                actor="critical_review",
                success=True,
                intent="lane_b_plan",
            )
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
