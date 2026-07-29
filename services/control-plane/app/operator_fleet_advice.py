"""Fleet-ranked grounded Advise for cross-workspace coaching (SA-1 + SA-2).

Builds a small fact pack from live operational state, picks one winner by
fixed urgency order, and renders a short deterministic coach line. Idle fleets
stay silent — no filler status copy.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.chat.command_intent import is_auto_complete_run_summary

# Ranking keys (highest first).
_RANK_PENDING_APPROVAL = 1
_RANK_CRITICAL_SIGNAL = 2
_RANK_REVIEW_READY = 3
_RANK_OPEN_HANDOFF = 4
_RANK_DEGRADED = 5


def workspace_advice_label(
    workspace_id: str | None,
    display_names: Mapping[str, str] | None = None,
) -> str:
    wid = str(workspace_id or "").strip()
    if not wid:
        return "another workspace"
    if display_names:
        named = str(display_names.get(wid) or "").strip()
        if named:
            return named
    suffix = wid.removeprefix("workspace_").replace("-", " ").replace("_", " ").strip()
    if not suffix:
        return wid
    return " ".join(part.capitalize() for part in suffix.split())


def _approval_workspace_id(record: dict[str, object]) -> str:
    return str(record.get("workspace_id") or "").strip()


def _collect_facts(
    *,
    active_run_records: list[dict[str, object]],
    pending_approval_records: list[dict[str, object]],
    fleet_signals: list[dict[str, object]],
    degraded: dict[str, object],
    watch_connected: bool,
    display_names: Mapping[str, str] | None,
    open_handoffs: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    facts: list[dict[str, object]] = []
    seen_approval_workspaces: set[str] = set()

    for record in pending_approval_records:
        workspace_id = _approval_workspace_id(record)
        if workspace_id in seen_approval_workspaces:
            continue
        seen_approval_workspaces.add(workspace_id)
        facts.append(
            {
                "kind": "pending_approval",
                "rank": _RANK_PENDING_APPROVAL,
                "workspace_id": workspace_id or None,
                "display_name": workspace_advice_label(workspace_id, display_names),
                "run_id": str(record.get("run_id") or "") or None,
                "signal_id": None,
                "title": str(record.get("summary") or record.get("title") or "").strip()
                or None,
            }
        )

    for run in active_run_records:
        if not bool(run.get("can_approve")) and run.get("phase") != "awaiting_approval":
            continue
        workspace_id = str(run.get("workspace_id") or "").strip()
        if workspace_id in seen_approval_workspaces:
            continue
        seen_approval_workspaces.add(workspace_id)
        facts.append(
            {
                "kind": "pending_approval",
                "rank": _RANK_PENDING_APPROVAL,
                "workspace_id": workspace_id or None,
                "display_name": workspace_advice_label(workspace_id, display_names),
                "run_id": str(run.get("run_id") or "") or None,
                "signal_id": None,
                "title": str(run.get("summary") or run.get("title") or "").strip() or None,
            }
        )

    for signal in fleet_signals:
        severity = str(signal.get("severity") or "info").strip().lower()
        if severity not in {"critical", "high"}:
            continue
        if str(signal.get("status") or "open").strip().lower() not in {"", "open"}:
            continue
        workspace_id = str(signal.get("workspace_id") or "").strip()
        title = str(signal.get("title") or "Critical signal").strip() or "Critical signal"
        facts.append(
            {
                "kind": "critical_signal",
                "rank": _RANK_CRITICAL_SIGNAL,
                "workspace_id": workspace_id or None,
                "display_name": workspace_advice_label(workspace_id, display_names),
                "run_id": None,
                "signal_id": str(signal.get("signal_id") or "") or None,
                "title": title,
            }
        )
        break

    for run in active_run_records:
        if run.get("phase") != "review_ready":
            continue
        if is_auto_complete_run_summary(str(run.get("summary") or "")):
            continue
        workspace_id = str(run.get("workspace_id") or "").strip()
        facts.append(
            {
                "kind": "review_ready",
                "rank": _RANK_REVIEW_READY,
                "workspace_id": workspace_id or None,
                "display_name": workspace_advice_label(workspace_id, display_names),
                "run_id": str(run.get("run_id") or "") or None,
                "signal_id": None,
                "title": str(run.get("summary") or run.get("title") or "").strip() or None,
            }
        )
        break

    for handoff in open_handoffs or []:
        target_id = str(handoff.get("target_workspace_id") or "").strip()
        if not target_id:
            continue
        task = str(handoff.get("task") or "").strip() or "Cross-workspace handoff"
        facts.append(
            {
                "kind": "open_handoff",
                "rank": _RANK_OPEN_HANDOFF,
                "workspace_id": target_id,
                "display_name": workspace_advice_label(target_id, display_names),
                "run_id": None,
                "signal_id": None,
                "handoff_id": str(handoff.get("handoff_id") or "") or None,
                "title": task,
                "source_workspace_id": str(handoff.get("source_workspace_id") or "") or None,
                "target_task_id": str(handoff.get("target_task_id") or "") or None,
            }
        )
        break

    if not watch_connected or bool(degraded.get("active")):
        reasons = degraded.get("reasons") if isinstance(degraded, dict) else None
        reason = ""
        if isinstance(reasons, list) and reasons:
            reason = str(reasons[0]).strip()
        facts.append(
            {
                "kind": "degraded_runtime",
                "rank": _RANK_DEGRADED,
                "workspace_id": None,
                "display_name": None,
                "run_id": None,
                "signal_id": None,
                "title": reason or None,
                "watch_connected": bool(watch_connected),
            }
        )

    return facts


def select_fleet_advice_winner(
    facts: list[dict[str, object]],
    *,
    focused_workspace_id: str | None = None,
) -> dict[str, object] | None:
    if not facts:
        return None
    focused = str(focused_workspace_id or "").strip()
    return sorted(
        facts,
        key=lambda item: (
            int(item.get("rank") or 99),
            # Same urgency: keep attention on the focused workspace when it ties.
            0 if focused and str(item.get("workspace_id") or "") == focused else 1,
            str(item.get("workspace_id") or ""),
            str(item.get("run_id") or item.get("signal_id") or item.get("handoff_id") or ""),
        ),
    )[0]


def build_fleet_advice_pack(
    *,
    active_run_records: list[dict[str, object]],
    pending_approval_records: list[dict[str, object]],
    fleet_signals: list[dict[str, object]],
    degraded: dict[str, object],
    watch_connected: bool,
    display_names: Mapping[str, str] | None = None,
    focused_workspace_id: str | None = None,
    scope_mode: str = "fleet",
    open_handoffs: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    focused = (focused_workspace_id or "").strip() or None
    facts = _collect_facts(
        active_run_records=active_run_records,
        pending_approval_records=pending_approval_records,
        fleet_signals=fleet_signals,
        degraded=degraded,
        watch_connected=watch_connected,
        display_names=display_names,
        open_handoffs=open_handoffs,
    )
    return {
        "scope_mode": "workspace" if scope_mode == "workspace" else "fleet",
        "focused_workspace_id": focused,
        "facts": facts,
        "winner": select_fleet_advice_winner(
            facts,
            focused_workspace_id=focused,
        ),
    }


def build_fleet_coach_line(
    fact: dict[str, object],
    *,
    focused_workspace_id: str | None = None,
    scope_mode: str = "fleet",
    display_names: Mapping[str, str] | None = None,
) -> str:
    kind = str(fact.get("kind") or "").strip()
    name = str(fact.get("display_name") or "").strip() or workspace_advice_label(
        str(fact.get("workspace_id") or ""),
        display_names,
    )
    focused = str(focused_workspace_id or "").strip()
    winner_workspace = str(fact.get("workspace_id") or "").strip()
    cross = bool(focused and winner_workspace and winner_workspace != focused)
    focus_label = workspace_advice_label(focused, display_names) if focused else ""

    if kind == "pending_approval":
        if cross and focus_label:
            return (
                f"Approve the guarded run in {name} before starting more "
                f"{focus_label} work."
            )
        if cross:
            return f"Approve the guarded run in {name} before continuing here."
        return f"Approve the guarded run in {name}."

    if kind == "critical_signal":
        title = str(fact.get("title") or "Critical signal").strip() or "Critical signal"
        title_l = title.lower()
        signal_detail = " ".join(
            [
                title,
                str(fact.get("summary") or ""),
                str(fact.get("detail") or ""),
                str(fact.get("reason") or ""),
            ]
        ).lower()
        if "github" in title_l and (
            "token" in signal_detail
            or "http 401" in signal_detail
            or "http 403" in signal_detail
            or "invalid credential" in signal_detail
            or "placeholder" in signal_detail
        ):
            if cross:
                return (
                    f"GitHub probe token for {name} is failing — "
                    "open Vault there and restore GH_TOKEN before continuing."
                )
            return (
                f"GitHub probe token is failing — open Vault and restore GH_TOKEN "
                f"({title})."
            )
        if "sentry" in title_l:
            if cross:
                return (
                    f"Sentry attention in {name} needs review; "
                    "switch there before continuing."
                )
            return f"Sentry attention needs review: {title}."
        if cross:
            return (
                f"Critical signal in {name} needs review; switch there before continuing."
            )
        if scope_mode == "fleet":
            return f"Critical signal in {name} needs review: {title}."
        return f"Critical signal needs review: {title}."

    if kind == "review_ready":
        if cross:
            return (
                f"Review the ready run in {name}; switch there before continuing."
            )
        return f"Review the ready run in {name}."

    if kind == "open_handoff":
        task = str(fact.get("title") or "the listed task").strip() or "the listed task"
        task_short = task if len(task) <= 72 else f"{task[:71].rstrip()}…"
        title_l = task.lower()
        auth_hint = ""
        if "401" in title_l or "unauthorized" in title_l or "github api" in title_l:
            auth_hint = " Fix GitHub credentials/token there;"
        if cross and focus_label:
            return (
                f"Handoff to {name} is open — switch there and finish “{task_short}”."
                f"{auth_hint} DashPro work waits until that closes."
                if focus_label.lower() in {"dashpro", "edu dash pro", "edudash"}
                else (
                    f"Handoff to {name} is open — switch there and finish “{task_short}”."
                    f"{auth_hint} Pause more {focus_label} work until that closes."
                )
            )
        if cross:
            return (
                f"Handoff to {name} is open — switch there and finish “{task_short}”."
                f"{auth_hint}".rstrip(";")
                + ("." if auth_hint else "")
            )
        return f"Finish the open handoff ticket in {name}: “{task_short}”."

    if kind == "degraded_runtime":
        if fact.get("watch_connected") is False:
            return "Check watch connectivity before continuing."
        title = str(fact.get("title") or "").strip()
        if title:
            return f"Inspect degraded runtime ({title}) before dispatching more work."
        return "Inspect degraded runtime before dispatching more work."

    return ""


def resolve_fleet_briefing_advise(
    *,
    pack: dict[str, object] | None,
    display_names: Mapping[str, str] | None = None,
) -> str | None:
    """Return a coach Advise line when fleet ranking applies; else None.

    None means the caller should keep the existing same-workspace Advise path.
    """
    if not isinstance(pack, dict):
        return None
    winner = pack.get("winner")
    if not isinstance(winner, dict):
        return None

    scope_mode = str(pack.get("scope_mode") or "fleet")
    focused = str(pack.get("focused_workspace_id") or "").strip() or None
    winner_workspace = str(winner.get("workspace_id") or "").strip()
    cross = bool(focused and winner_workspace and winner_workspace != focused)
    use_coach = scope_mode == "fleet" or cross

    if not use_coach:
        # Focused workspace owns the winning fact — keep local next-safe-action copy.
        return None

    line = build_fleet_coach_line(
        winner,
        focused_workspace_id=focused,
        scope_mode=scope_mode,
        display_names=display_names,
    )
    return line or None
