"""Operator briefing projection for the control-plane thin slice."""

from __future__ import annotations

from app.chat.command_intent import humanize_run_summary, is_auto_complete_run_summary
from app.operator_briefing_signals import filter_actionable_inbox_items, is_monitor_signal
from app.inbox_projection import WatchInboxFetcher, build_inbox_response
from app.operator_fleet_advice import build_fleet_advice_pack
from app.runs.service import (
    list_operator_facing_active_runs,
    list_pending_approval_records,
    to_runtime_summary_active_run,
)
from app.persistence import operator_presence_settings_store
from app.host_context.reminders import due_reminders
from app.persistence.operator_memory_store import search_memories
from app.operator_briefing_rhythm import build_operator_briefing_rhythm
from app.operator_presence import build_operator_presence
from app.production_readiness import build_production_readiness
from app.runtime_summary_assembler import WatchProbe, assemble_runtime_summary
from app.workspace_project_bindings import load_workspace_project_bindings


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
            if run.get("phase") == "review_ready" and is_auto_complete_run_summary(
                str(run.get("summary", "")),
            ):
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
        signal_title = str(signal.get("title") or "top signal").strip() or "top signal"
        actions.append(
            {
                "action_id": f"review_{signal_id}",
                "kind": "review_signal",
                "title": signal_title,
                "detail": f"Inspect {signal_title}.",
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


def _filter_records_by_workspace(
    records: list[dict[str, object]],
    workspace_id: str | None,
) -> list[dict[str, object]]:
    if not workspace_id:
        return records
    return [
        record
        for record in records
        if str(record.get("workspace_id", "")).strip() == workspace_id
    ]


def _memory_highlights(
    *,
    workspace_id: str | None,
    top_signals: list[dict[str, object]],
    rhythm: dict[str, str],
) -> list[dict[str, object]]:
    """Prefer due reminders; fall back to lexical memory matches."""
    due = due_reminders(workspace_id=workspace_id, limit=3)
    if due:
        return [dict(item) for item in due[:3]]

    candidate_text = " ".join(
        [
            rhythm.get("notice", ""),
            rhythm.get("advise", ""),
            *(str(item.get("title") or "") for item in top_signals[:2]),
        ]
    )
    seen: set[str] = set()
    matches: list[dict[str, object]] = []
    for token in candidate_text.split():
        normalized = token.strip(" ,.:;!?()[]{}").lower()
        if len(normalized) < 4 or normalized in seen:
            continue
        seen.add(normalized)
        for item in search_memories(normalized, workspace_id=workspace_id, limit=2):
            memory_id = str(item.get("memory_id") or "")
            if memory_id and all(memory_id != str(existing.get("memory_id")) for existing in matches):
                matches.append(item)
            if len(matches) >= 2:
                return matches
    return matches


def build_operator_briefing(
    *,
    watch_probe: WatchProbe | None = None,
    inbox_fetcher: WatchInboxFetcher | None = None,
    viewport_compact: bool = False,
    workspace_id: str | None = None,
    light: bool = False,
) -> dict[str, object]:
    runtime_summary = assemble_runtime_summary(
        watch_probe=watch_probe,
        inbox_fetcher=inbox_fetcher,
        light=light,
    )
    watch_connected = bool(runtime_summary["watch"]["connected"])
    if light:
        # Keep presence ticks cheap: reuse empty inbox; full briefing still loads signals.
        inbox_snapshot = {
            "items": [],
            "count": 0,
            "updated_at": runtime_summary["generated_at"],
        }
    else:
        inbox_snapshot = (
            build_inbox_response(
                inbox_fetcher=inbox_fetcher,
                allow_empty_unavailable=True,
            )
            if watch_connected
            else {"items": [], "count": 0, "updated_at": runtime_summary["generated_at"]}
        )
    top_signals = [
        item for item in inbox_snapshot.get("items", []) if isinstance(item, dict)
    ]
    if any(is_monitor_signal(item) for item in top_signals):
        top_signals = filter_actionable_inbox_items(top_signals)
    scoped_workspace_id = workspace_id.strip() if workspace_id else None

    def _signal_priority(item: dict[str, object]) -> tuple[int, str]:
        signal_id = str(item.get("signal_id", ""))
        title = str(item.get("title", "")).lower()
        meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
        if meta.get("signal_family") == "child_project_monitor":
            return (0, signal_id)
        if signal_id in {
            "signal_runtime_summary_degraded",
            "signal_watch_bootstrap_ready",
        } or "bootstrap" in title:
            return (3, signal_id)
        severity = str(item.get("severity", "info"))
        rank = 1 if severity in {"critical", "high"} else 2
        return (rank, signal_id)

    fleet_signals = sorted(top_signals, key=_signal_priority)
    if scoped_workspace_id:
        top_signals = [
            item
            for item in fleet_signals
            if str(item.get("workspace_id", "")).strip() in {"", scoped_workspace_id}
        ]
    else:
        top_signals = fleet_signals
    top_signals = top_signals[:3]

    fleet_active_run_records = list_operator_facing_active_runs()
    fleet_pending_approval_records = list_pending_approval_records()
    active_run_records = fleet_active_run_records
    pending_approval_records = fleet_pending_approval_records
    if scoped_workspace_id:
        active_run_records = _filter_records_by_workspace(
            fleet_active_run_records,
            scoped_workspace_id,
        )
        pending_approval_records = _filter_records_by_workspace(
            fleet_pending_approval_records,
            scoped_workspace_id,
        )
    active_runs = [
        to_runtime_summary_active_run(record) for record in active_run_records
    ]
    next_safe_actions = _build_next_safe_actions(
        active_run_records=active_run_records,
        top_signals=top_signals,
        degraded_active=bool(runtime_summary["degraded"]["active"]),
    )
    pending_approvals_count = len(pending_approval_records)
    display_names = {
        workspace_key: str(binding.display_name).strip()
        for workspace_key, binding in load_workspace_project_bindings().items()
        if binding.display_name and str(binding.display_name).strip()
    }
    scope_mode = "workspace" if scoped_workspace_id else "fleet"
    open_handoffs: list[dict[str, object]] = []
    try:
        from app.persistence.handoff_store import list_open_follow_through_handoffs

        open_handoffs = list(list_open_follow_through_handoffs(limit=20))
    except Exception:  # noqa: BLE001 — briefing must stay available
        open_handoffs = []
    fleet_advice_pack = build_fleet_advice_pack(
        active_run_records=fleet_active_run_records,
        pending_approval_records=fleet_pending_approval_records,
        fleet_signals=fleet_signals,
        degraded=runtime_summary["degraded"],
        watch_connected=watch_connected,
        display_names=display_names,
        focused_workspace_id=scoped_workspace_id,
        scope_mode=scope_mode,
        open_handoffs=open_handoffs,
    )
    lead_awaiting_engagement_count = 0
    try:
        from app.workspace_agents.lead_vaxon_handoff import count_awaiting_engagement_plans

        lead_awaiting_engagement_count = count_awaiting_engagement_plans(
            workspace_id=scoped_workspace_id,
        )
    except Exception:  # noqa: BLE001 — briefing must stay available
        lead_awaiting_engagement_count = 0
    rhythm = build_operator_briefing_rhythm(
        active_runs=active_runs,
        top_signals=top_signals,
        pending_approvals_count=pending_approvals_count,
        degraded=runtime_summary["degraded"],
        watch_connected=watch_connected,
        next_safe_actions=next_safe_actions,
        cli_runtime=runtime_summary.get("cli_runtime"),
        fleet_advice_pack=fleet_advice_pack,
        display_names=display_names,
        lead_awaiting_engagement_count=lead_awaiting_engagement_count,
    )

    scope: dict[str, object] = (
        {"mode": "workspace", "workspace_id": scoped_workspace_id}
        if scoped_workspace_id
        else {"mode": "fleet"}
    )

    due = [] if light else due_reminders(workspace_id=scoped_workspace_id, limit=5)
    host_artifacts: list[dict[str, object]] = []
    if not light:
        try:
            from app.host_context.service import list_artifacts as list_host_artifacts

            host_artifacts = list(list_host_artifacts(limit=5).get("items") or [])
        except Exception:  # noqa: BLE001 — briefing must stay available
            host_artifacts = []

    presence_settings = operator_presence_settings_store.load_settings()
    autonomy_mode = str(presence_settings.get("autonomy_mode") or "manual").strip().lower()
    if autonomy_mode not in {"manual", "semi", "full"}:
        autonomy_mode = "manual"
    scheduler_effective = False
    try:
        from app.workspace_agents.scheduler import scheduler_enabled

        scheduler_effective = bool(scheduler_enabled())
    except Exception:  # noqa: BLE001 — briefing must stay available
        scheduler_effective = False

    critical_signal_count = sum(
        1
        for item in top_signals
        if isinstance(item, dict) and str(item.get("severity", "")).lower() == "critical"
    )
    degraded_payload = runtime_summary["degraded"]
    degraded_reasons = (
        list(degraded_payload.get("reasons") or [])
        if isinstance(degraded_payload, dict)
        else []
    )
    production_readiness = build_production_readiness(
        watch_connected=bool(runtime_summary["watch"]["connected"]),
        control_plane_ready=bool(runtime_summary["control_plane"]["ready"]),
        degraded_active=bool(degraded_payload.get("active"))
        if isinstance(degraded_payload, dict)
        else False,
        degraded_reasons=[str(item) for item in degraded_reasons],
        cli_runtime=(
            runtime_summary.get("cli_runtime")
            if isinstance(runtime_summary.get("cli_runtime"), dict)
            else None
        ),
        critical_signal_count=critical_signal_count,
        pending_approvals=pending_approvals_count,
        autonomy_mode=autonomy_mode,
        scheduler_effective=scheduler_effective,
    )

    connectivity = {
        "control_plane_ready": bool(runtime_summary["control_plane"]["ready"]),
        "watch_connected": bool(runtime_summary["watch"]["connected"]),
    }

    return {
        "generated_at": runtime_summary["generated_at"],
        "scope": scope,
        "notice": rhythm["notice"],
        "advise": rhythm["advise"],
        "advise_ui_action": rhythm.get("advise_ui_action"),
        "executive_rhythm": rhythm,
        "top_signals": top_signals,
        "pending_approvals": {
            "count": pending_approvals_count,
            "items": pending_approval_records,
        },
        "active_runs": active_runs,
        "next_safe_actions": next_safe_actions,
        "awaiting_engagement_count": lead_awaiting_engagement_count
        + sum(1 for run in active_runs if run.get("phase") == "review_ready"),
        "degraded": runtime_summary["degraded"],
        "cli_runtime": runtime_summary.get("cli_runtime", {}),
        "connectivity": connectivity,
        "production_readiness": production_readiness,
        "memory_highlights": (
            []
            if light
            else _memory_highlights(
                workspace_id=scoped_workspace_id,
                top_signals=top_signals,
                rhythm=rhythm,
            )
        ),
        "due_reminders": due,
        "host_artifacts": host_artifacts,
        "operator_presence": build_operator_presence(
            {
                "top_signals": top_signals,
                "pending_approvals": {
                    "count": runtime_summary["approvals"]["pending_count"],
                },
                "degraded": runtime_summary["degraded"],
                "connectivity": connectivity,
                "notice": rhythm["notice"],
                "advise": rhythm["advise"],
                "production_readiness": production_readiness,
            },
            viewport_compact=viewport_compact,
            settings=presence_settings,
        ),
    }
