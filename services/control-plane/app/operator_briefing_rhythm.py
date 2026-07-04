"""Notice/Advise rhythm strings for the operator briefing projection."""

from __future__ import annotations


def _review_ready_runs(active_runs: list[dict[str, object]]) -> list[dict[str, object]]:
    return [run for run in active_runs if run.get("phase") == "review_ready"]


def build_briefing_notice(
    *,
    active_runs: list[dict[str, object]],
    top_signals: list[dict[str, object]],
    pending_approvals_count: int,
    degraded: dict[str, object],
    watch_connected: bool,
) -> str:
    if pending_approvals_count > 0:
        noun = "run" if pending_approvals_count == 1 else "runs"
        return f"{pending_approvals_count} {noun} awaiting explicit approval."

    review_ready = _review_ready_runs(active_runs)
    if review_ready:
        if len(review_ready) == 1:
            title = str(review_ready[0].get("title") or review_ready[0].get("run_id") or "Run")
            return f"{title} is ready for operator review."
        return f"{len(review_ready)} runs are ready for operator review."

    if top_signals:
        signal = top_signals[0]
        severity = str(signal.get("severity", "info"))
        title = str(signal.get("title", "Top signal"))
        if severity in {"high", "critical"}:
            return f"High-priority signal: {title}."
        return f"Open signal needs review: {title}."

    if not watch_connected:
        return "Watch disconnected; signal inbox is unavailable."

    if bool(degraded.get("active")):
        reasons = degraded.get("reasons")
        if isinstance(reasons, list) and reasons:
            joined = ", ".join(str(reason) for reason in reasons)
            return f"Runtime degraded — {joined}."
        return "Runtime degraded — check connectivity before dispatching work."

    count = len(active_runs)
    if count == 0:
        return "No active runs. Systems nominal."

    noun = "run" if count == 1 else "runs"
    return f"{count} active {noun} in flight."


def build_briefing_advise(
    *,
    next_safe_actions: list[dict[str, object]],
    active_runs: list[dict[str, object]],
) -> str:
    if next_safe_actions:
        action = next_safe_actions[0]
        detail = str(action.get("detail", "")).strip()
        if detail:
            return detail
        title = str(action.get("title", "")).strip()
        if title:
            return title
        return "Review the recommended next action."

    if _review_ready_runs(active_runs):
        return "Review execution evidence in Command or Active Run when ready."

    return "Describe the next operator action in Command."


def build_operator_briefing_rhythm(
    *,
    active_runs: list[dict[str, object]],
    top_signals: list[dict[str, object]],
    pending_approvals_count: int,
    degraded: dict[str, object],
    watch_connected: bool,
    next_safe_actions: list[dict[str, object]],
) -> dict[str, str]:
    return {
        "notice": build_briefing_notice(
            active_runs=active_runs,
            top_signals=top_signals,
            pending_approvals_count=pending_approvals_count,
            degraded=degraded,
            watch_connected=watch_connected,
        ),
        "advise": build_briefing_advise(
            next_safe_actions=next_safe_actions,
            active_runs=active_runs,
        ),
    }
