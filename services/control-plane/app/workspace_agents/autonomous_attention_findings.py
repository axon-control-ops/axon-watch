"""Finding collectors for the bounded autonomous attention loop."""

from __future__ import annotations

from typing import Any

from app.persistence import handoff_store
from app.workspace_agents.lead_checkin_assign import (
    SPECIALIST_ROLES,
    LeadCheckinFinding,
    assign_owner_role_for_monitor,
)
from app.workspace_agents.lead_team_checkin import collect_workspace_findings


def collect_signal_findings(
    workspace_id: str,
    *,
    signals: list[dict[str, Any]] | None = None,
) -> list[LeadCheckinFinding]:
    findings: list[LeadCheckinFinding] = []
    rows = signals
    if rows is None:
        try:
            from app.adapters.watch_client import fetch_watch_inbox

            payload = fetch_watch_inbox(timeout_seconds=2.0, allow_stale=True, cached_only=True)
            raw = payload.get("items") if isinstance(payload, dict) else None
            rows = raw if isinstance(raw, list) else []
        except Exception:  # noqa: BLE001 — attend must stay fail-open
            rows = []
    for signal in rows or []:
        if not isinstance(signal, dict):
            continue
        signal_workspace = str(signal.get("workspace_id") or "").strip()
        if signal_workspace and signal_workspace != workspace_id:
            continue
        status = str(signal.get("status") or "open").strip().lower()
        if status not in {"", "open"}:
            continue
        severity = str(signal.get("severity") or "info").strip().lower()
        if severity not in {"critical", "high", "medium", "warning"}:
            continue
        signal_id = str(signal.get("signal_id") or "").strip() or "signal"
        title = str(signal.get("title") or "Signal").strip() or "Signal"
        detail = str(signal.get("detail") or signal.get("summary") or "").strip()
        kind = "critical_signal" if severity == "critical" else "warning_signal"
        owner = assign_owner_role_for_monitor(
            str(signal.get("kind") or signal.get("check_type") or ""),
            title,
        )
        findings.append(
            LeadCheckinFinding(
                kind=kind,
                workspace_id=workspace_id,
                owner_role=owner,
                title=title,
                detail=detail or f"{signal_id} severity={severity}",
                dedupe_key=f"signal:{workspace_id}:{signal_id}:{severity}",
                escalate_only=severity == "critical",
            )
        )
    return findings


def collect_handoff_findings(
    workspace_id: str,
    *,
    handoffs: list[dict[str, Any]] | None = None,
) -> list[LeadCheckinFinding]:
    findings: list[LeadCheckinFinding] = []
    rows = handoffs
    if rows is None:
        try:
            rows = handoff_store.list_open_follow_through_handoffs(limit=40)
        except Exception:  # noqa: BLE001
            rows = []
    for handoff in rows or []:
        if not isinstance(handoff, dict):
            continue
        target = str(handoff.get("target_workspace_id") or "").strip()
        if workspace_id != target:
            continue
        if str(handoff.get("target_task_id") or "").strip():
            continue
        handoff_id = str(handoff.get("handoff_id") or "").strip() or "handoff"
        task = str(handoff.get("task") or "").strip() or "Open handoff"
        routed = str(handoff.get("routed_role") or "").strip().lower() or "watcher"
        if routed not in SPECIALIST_ROLES:
            routed = "watcher"
        findings.append(
            LeadCheckinFinding(
                kind="open_handoff",
                workspace_id=target or workspace_id,
                owner_role=routed,
                title=f"Handoff follow-through: {task[:80]}",
                detail=str(handoff.get("reason") or task).strip(),
                dedupe_key=f"handoff:{handoff_id}",
                escalate_only=False,
            )
        )
    return findings


def collect_attend_findings(
    workspace_id: str,
    *,
    monitors_payload: dict[str, Any] | None = None,
    connectors_payload: dict[str, Any] | None = None,
    signals: list[dict[str, Any]] | None = None,
    handoffs: list[dict[str, Any]] | None = None,
) -> list[LeadCheckinFinding]:
    base = collect_workspace_findings(
        workspace_id,
        monitors_payload=monitors_payload,
        connectors_payload=connectors_payload,
    )
    return (
        base
        + collect_signal_findings(workspace_id, signals=signals)
        + collect_handoff_findings(workspace_id, handoffs=handoffs)
    )
