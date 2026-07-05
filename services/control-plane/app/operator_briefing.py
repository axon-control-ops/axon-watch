"""Operator briefing projection for the control-plane thin slice."""

from __future__ import annotations

from app.chat.command_intent import humanize_run_summary
from app.inbox_projection import WatchInboxFetcher, build_inbox_response
from app.runs.service import (
    list_active_runs,
    list_pending_approval_records,
    to_runtime_summary_active_run,
)
from app.persistence import operator_presence_settings_store
from app.operator_briefing_rhythm import build_operator_briefing_rhythm
from app.operator_presence import build_operator_presence
from app.runtime_summary_assembler import WatchProbe, assemble_runtime_summary


def _build_next_safe_actions(
    *,
    active_run_records: list[dict[str, object]],
    top_signals: list[dict[str, object]],
    degraded_active: bool,
) -> list[dict[str, object]]:
    actions: list[dict[str, object]] = []

    for run in active_run_records:
        if bool(run.get("can_approve")):
            run_id = str(run.get("run_id", ""))
            summary = humanize_run_summary(str(run.get("summary", "this run")))
            actions.append(
                {
                    "action_id": f"approve_{run_id}",
                    "kind": "approve_run",
                    "title": "Approve guarded run",
                    "detail": f"Approve {summary} to continue execution.",
                    "workspace_id": str(run.get("workspace_id", "")) or None,
                    "run_id": run_id or None,
                    "signal_id": None,
                }
            )
            break

    for run in active_run_records:
        if bool(run.get("can_resume")):
            if bool(run.get("can_approve")):
                continue
            run_id = str(run.get("run_id", ""))
            summary = humanize_run_summary(str(run.get("summary", "this run")))
            actions.append(
                {
                    "action_id": f"resume_{run_id}",
                    "kind": "resume_run",
                    "title": "Resume paused run",
                    "detail": f"Resume {summary}.",
                    "workspace_id": str(run.get("workspace_id", "")) or None,
                    "run_id": run_id or None,
                    "signal_id": None,
                }
            )
            break

    if top_signals:
        signal = top_signals[0]
        signal_id = str(signal.get("signal_id", ""))
        actions.append(
            {
                "action_id": f"review_{signal_id}",
                "kind": "review_signal",
                "title": "Review top signal",
                "detail": f"Inspect {signal.get('title', 'top signal')}.",
                "workspace_id": str(signal.get("workspace_id", "")) or None,
                "run_id": None,
                "signal_id": signal_id or None,
            }
        )

    if degraded_active:
        actions.append(
            {
                "action_id": "inspect_runtime_degraded",
                "kind": "inspect_runtime",
                "title": "Inspect degraded runtime",
                "detail": "Check degraded connectivity or runtime state before dispatching more work.",
                "workspace_id": None,
                "run_id": None,
                "signal_id": None,
            }
        )

    return actions


def build_operator_briefing(
    *,
    watch_probe: WatchProbe | None = None,
    inbox_fetcher: WatchInboxFetcher | None = None,
    viewport_compact: bool = False,
) -> dict[str, object]:
    runtime_summary = assemble_runtime_summary(
        watch_probe=watch_probe,
        inbox_fetcher=inbox_fetcher,
    )
    watch_connected = bool(runtime_summary["watch"]["connected"])
    inbox_snapshot = (
        build_inbox_response(inbox_fetcher=inbox_fetcher)
        if watch_connected
        else {"items": [], "count": 0, "updated_at": runtime_summary["generated_at"]}
    )
    top_signals = [
        item for item in inbox_snapshot.get("items", []) if isinstance(item, dict)
    ][:3]
    active_run_records = list_active_runs()
    pending_approval_records = list_pending_approval_records()
    active_runs = [
        to_runtime_summary_active_run(record) for record in active_run_records
    ]
    next_safe_actions = _build_next_safe_actions(
        active_run_records=active_run_records,
        top_signals=top_signals,
        degraded_active=bool(runtime_summary["degraded"]["active"]),
    )
    rhythm = build_operator_briefing_rhythm(
        active_runs=active_runs,
        top_signals=top_signals,
        pending_approvals_count=int(runtime_summary["approvals"]["pending_count"]),
        degraded=runtime_summary["degraded"],
        watch_connected=watch_connected,
        next_safe_actions=next_safe_actions,
    )

    return {
        "generated_at": runtime_summary["generated_at"],
        "notice": rhythm["notice"],
        "advise": rhythm["advise"],
        "executive_rhythm": rhythm,
        "top_signals": top_signals,
        "pending_approvals": {
            "count": runtime_summary["approvals"]["pending_count"],
            "items": pending_approval_records,
        },
        "active_runs": active_runs,
        "next_safe_actions": next_safe_actions,
        "degraded": runtime_summary["degraded"],
        "connectivity": {
            "control_plane_ready": bool(runtime_summary["control_plane"]["ready"]),
            "watch_connected": bool(runtime_summary["watch"]["connected"]),
        },
        "operator_presence": build_operator_presence(
            {
                "top_signals": top_signals,
                "pending_approvals": {
                    "count": runtime_summary["approvals"]["pending_count"],
                },
                "degraded": runtime_summary["degraded"],
                "connectivity": {
                    "watch_connected": bool(runtime_summary["watch"]["connected"]),
                },
            },
            viewport_compact=viewport_compact,
            settings=operator_presence_settings_store.load_settings(),
        ),
    }
