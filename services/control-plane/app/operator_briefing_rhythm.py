"""Notice/Advise/Decide/Execute/Verify/Report rhythm for operator briefing."""

from __future__ import annotations

EXECUTIVE_RHYTHM_KEYS = ("notice", "advise", "decide", "execute", "verify", "report")


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


def build_briefing_decide(
    *,
    pending_approvals_count: int,
    active_runs: list[dict[str, object]],
    top_signals: list[dict[str, object]],
    degraded: dict[str, object],
) -> str:
    if pending_approvals_count > 0:
        noun = "run" if pending_approvals_count == 1 else "runs"
        return f"Decide whether to approve or reject the guarded {noun} before execution continues."

    review_ready = _review_ready_runs(active_runs)
    if review_ready:
        if len(review_ready) == 1:
            title = str(review_ready[0].get("title") or review_ready[0].get("run_id") or "run")
            return f"Decide whether to resume, complete, or discard {title}."
        return "Decide whether to resume, complete, or discard the review-ready runs."

    if top_signals:
        signal = top_signals[0]
        title = str(signal.get("title", "top signal"))
        watch_rule = signal.get("watch_rule")
        mode = (
            str(watch_rule.get("mode", "observe")).strip().lower()
            if isinstance(watch_rule, dict)
            else "observe"
        )
        if mode in {"approval", "execute"}:
            return f"Decide whether to act on interruptive signal: {title}."
        return f"Decide whether to review signal: {title}."

    if bool(degraded.get("active")):
        return "Decide whether to inspect degraded runtime before dispatching more work."

    return "No immediate decision required. Assign the next focus when ready."


def build_briefing_execute(*, next_safe_actions: list[dict[str, object]]) -> str:
    if not next_safe_actions:
        return "Execute the next operator command from Command when you are ready."

    action = next_safe_actions[0]
    kind = str(action.get("kind", "")).strip()
    by_kind = {
        "approve_run": "Execute: approve the guarded run to unblock execution.",
        "resume_run": "Execute: resume the paused run.",
        "review_signal": "Execute: review the top signal in Attention.",
        "inspect_runtime": "Execute: inspect degraded runtime before continuing.",
    }
    if kind in by_kind:
        return by_kind[kind]

    title = str(action.get("title", "")).strip()
    if title:
        return f"Execute: {title}."
    return "Execute the recommended next safe action."


def build_briefing_verify(
    *,
    pending_approvals_count: int,
    active_runs: list[dict[str, object]],
    degraded: dict[str, object],
    watch_connected: bool,
) -> str:
    if pending_approvals_count > 0:
        return "Verify approval boundary blocks execution until you decide."

    review_ready = _review_ready_runs(active_runs)
    if review_ready:
        return "Verify run history receipts before completing review-ready work."

    executing = [run for run in active_runs if run.get("phase") == "executing"]
    if executing:
        return "Verify run phase and history receipts match expected progress."

    if bool(degraded.get("active")):
        return "Verify watch connectivity and runtime summary state before continuing."

    if not watch_connected:
        return "Verify watch service connectivity before relying on the signal inbox."

    return "Verify runtime summary and inbox agree before dispatching work."


def build_briefing_report(
    *,
    pending_approvals_count: int,
    top_signals: list[dict[str, object]],
    active_runs: list[dict[str, object]],
    degraded: dict[str, object],
) -> str:
    parts: list[str] = []
    if pending_approvals_count > 0:
        noun = "approval" if pending_approvals_count == 1 else "approvals"
        parts.append(f"{pending_approvals_count} pending {noun}")
    if top_signals:
        noun = "signal" if len(top_signals) == 1 else "signals"
        parts.append(f"{len(top_signals)} surfaced {noun}")
    if active_runs:
        noun = "run" if len(active_runs) == 1 else "runs"
        parts.append(f"{len(active_runs)} active {noun}")
    if bool(degraded.get("active")):
        parts.append("runtime degraded")

    if not parts:
        return "Report: systems nominal; no active operator decisions."

    return f"Report: {', '.join(parts)}."


def build_operator_briefing_rhythm(
    *,
    active_runs: list[dict[str, object]],
    top_signals: list[dict[str, object]],
    pending_approvals_count: int,
    degraded: dict[str, object],
    watch_connected: bool,
    next_safe_actions: list[dict[str, object]],
) -> dict[str, str]:
    notice = build_briefing_notice(
        active_runs=active_runs,
        top_signals=top_signals,
        pending_approvals_count=pending_approvals_count,
        degraded=degraded,
        watch_connected=watch_connected,
    )
    advise = build_briefing_advise(
        next_safe_actions=next_safe_actions,
        active_runs=active_runs,
    )
    return {
        "notice": notice,
        "advise": advise,
        "decide": build_briefing_decide(
            pending_approvals_count=pending_approvals_count,
            active_runs=active_runs,
            top_signals=top_signals,
            degraded=degraded,
        ),
        "execute": build_briefing_execute(next_safe_actions=next_safe_actions),
        "verify": build_briefing_verify(
            pending_approvals_count=pending_approvals_count,
            active_runs=active_runs,
            degraded=degraded,
            watch_connected=watch_connected,
        ),
        "report": build_briefing_report(
            pending_approvals_count=pending_approvals_count,
            top_signals=top_signals,
            active_runs=active_runs,
            degraded=degraded,
        ),
    }
