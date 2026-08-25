"""Deterministic operator REPORT lane — roster + briefing + verified handoffs.

Never invokes Lane B / IDE Composer. Never repeats raw specialist transcripts.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.kairo.report_next_move import (
    degraded_reasons as _degraded_reasons,
    next_move as _next_move,
    remote_ingress_soft as _remote_ingress_soft,
)
from app.kairo.operator_report_intent import is_operator_report_request
from app.kairo.operator_fleet_report import (
    collect_workspace_reports,
    fingerprint_rows,
    fleet_lead_rollup_bits,
    live_fleet_health,
    render_report_text,
    workspace_update_bits,
)
from app.kairo.report_text import (
    _scrub_operator_line,
    _truncate,
)
from app.kairo.verified_handoff_index import list_verified_lead_handoffs
from app.operator_briefing_signals import is_bootstrap_signal

_BUSY_STATUSES = frozenset(
    {
        "executing",
        "planning",
        "verifying",
        "blocked",
        "waiting_approval",
        "assigned",
    }
)

_NUMBER_WORDS = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
}


def _spell_count(n: int) -> str:
    return _NUMBER_WORDS.get(int(n), str(int(n)))


def _employee_rows(company: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(company, dict):
        return []
    employees = company.get("employees")
    if not isinstance(employees, list):
        return []
    return [row for row in employees if isinstance(row, dict)]


def _is_busy(row: dict[str, Any]) -> bool:
    if str(row.get("active_run_id") or "").strip():
        return True
    status = str(row.get("status") or "").strip().lower()
    return status in _BUSY_STATUSES


def _is_recently_completed(row: dict[str, Any]) -> bool:
    if _is_busy(row):
        return False
    return str(row.get("last_outcome") or "").strip().lower() == "completed"


def _failed_rows(
    rows: list[dict[str, Any]],
    *,
    dispatch_ready: bool = False,
) -> list[dict[str, Any]]:
    """Actionable failures only — skip busy roles and healed auth/CLI timeouts."""
    out: list[dict[str, Any]] = []
    for row in rows:
        if _is_busy(row):
            continue
        outcome = str(row.get("last_outcome") or "").strip().lower()
        if outcome != "failed":
            continue
        if _is_resolved_auth_failure(row, dispatch_ready=dispatch_ready):
            continue
        out.append(row)
    return out


_AUTH_FAILURE_MARKERS = (
    "auth probe timed out",
    "no cli runtime is ready",
    "cursor cli auth",
    "runtime login is not ready",
    "cli (local) unavailable",
    "open runtime or vault",
)


def _cli_dispatch_ready(
    snapshot: dict[str, Any] | None = None,
    *,
    briefing: dict[str, Any] | None = None,
) -> bool:
    source = briefing if isinstance(briefing, dict) else None
    if source is None and isinstance(snapshot, dict):
        raw = snapshot.get("briefing")
        source = raw if isinstance(raw, dict) else {}
    cli = (source or {}).get("cli_runtime") if isinstance(source, dict) else {}
    if not isinstance(cli, dict):
        return False
    return bool(cli.get("dispatch_ready"))


def _is_auth_runtime_failure_detail(detail: str) -> bool:
    lowered = str(detail or "").strip().lower()
    if not lowered:
        return False
    return any(marker in lowered for marker in _AUTH_FAILURE_MARKERS)


def _is_resolved_auth_failure(row: dict[str, Any], *, dispatch_ready: bool) -> bool:
    if not dispatch_ready:
        return False
    detail = str(row.get("last_outcome_detail") or row.get("detail") or "").strip()
    return _is_auth_runtime_failure_detail(detail)


def _handoff_is_stale_auth_rollup(handoff: dict[str, Any], *, dispatch_ready: bool) -> bool:
    if not dispatch_ready:
        return False
    hay = " ".join(
        [
            str(handoff.get("headline") or ""),
            str(handoff.get("lead_summary") or ""),
            str(handoff.get("lead_next") or ""),
        ]
    )
    return _is_auth_runtime_failure_detail(hay)


def _fresh_handoffs(
    handoffs: list[dict[str, Any]],
    *,
    dispatch_ready: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen_employees: set[str] = set()
    for handoff in handoffs:
        if not isinstance(handoff, dict):
            continue
        if _handoff_is_stale_auth_rollup(handoff, dispatch_ready=dispatch_ready):
            continue
        employee_key = (
            str(handoff.get("employee_name") or "").strip().lower()
            or str(handoff.get("run_id") or "").strip()
            or str(handoff.get("receipt_id") or "").strip()
        )
        if employee_key and employee_key in seen_employees:
            continue
        if employee_key:
            seen_employees.add(employee_key)
        out.append(handoff)
    return out


def _name_role(row: dict[str, Any]) -> str:
    name = str(row.get("name") or "").strip() or "Teammate"
    role = str(row.get("role_label") or row.get("role") or "").strip()
    if role:
        return f"{name} ({role})"
    return name


def _roster_snapshot(
    workspace_id: str | None,
    *,
    dispatch_ready: bool = False,
) -> dict[str, Any]:
    cleaned = str(workspace_id or "").strip()
    if not cleaned:
        return {
            "workspace_id": "",
            "company_name": "",
            "employees": [],
            "busy": [],
            "completed": [],
            "failed": [],
        }
    from app.workspace_agents import build_company_roster

    try:
        company = build_company_roster(cleaned)
    except Exception:
        company = {}
    rows = _employee_rows(company if isinstance(company, dict) else None)
    busy = [row for row in rows if _is_busy(row)]
    completed = [row for row in rows if _is_recently_completed(row)]
    failed = _failed_rows(rows, dispatch_ready=dispatch_ready)
    # Stable ordering: role then name.
    busy.sort(key=lambda r: (str(r.get("role") or ""), str(r.get("name") or "")))
    completed.sort(key=lambda r: (str(r.get("role") or ""), str(r.get("name") or "")))
    failed.sort(key=lambda r: (str(r.get("role") or ""), str(r.get("name") or "")))
    return {
        "workspace_id": cleaned,
        "company_name": str((company or {}).get("company_name") or cleaned),
        "employees": rows,
        "busy": busy,
        "completed": completed,
        "failed": failed,
    }


def build_operator_report_snapshot(
    *,
    workspace_id: str | None,
    pack: dict[str, Any] | None = None,
    force_refresh: bool = True,
) -> dict[str, Any]:
    """Fresh snapshot for REPORT — briefing + live roster + verified handoffs."""
    del force_refresh  # callers force-refresh the pack; snapshot always reads live ledger
    briefing = (pack or {}).get("briefing") if isinstance(pack, dict) else None
    if not isinstance(briefing, dict):
        from app.operator_briefing import build_operator_briefing

        briefing = build_operator_briefing(workspace_id=workspace_id)
    fleet = (pack or {}).get("fleet") if isinstance(pack, dict) else {}
    if not isinstance(fleet, dict):
        fleet = {}
    # REPORT is the explicit request that expands count-only context fleet data.
    fleet = live_fleet_health(fleet)

    scoped = str(workspace_id or "").strip() or str(
        (briefing.get("scope") or {}).get("workspace_id") or ""
    ).strip()
    dispatch_ready = _cli_dispatch_ready(briefing=briefing)
    roster = _roster_snapshot(scoped or None, dispatch_ready=dispatch_ready)
    handoffs = _fresh_handoffs(
        list_verified_lead_handoffs(workspace_id=scoped or None, limit=8),
        dispatch_ready=dispatch_ready,
    )

    workspace_reports = collect_workspace_reports(
        fleet=fleet,
        scoped_workspace_id=scoped,
        scoped_roster=roster,
        scoped_handoffs=handoffs,
        roster_loader=lambda workspace: _roster_snapshot(
            workspace, dispatch_ready=dispatch_ready
        ),
        handoff_loader=lambda workspace: _fresh_handoffs(
            list_verified_lead_handoffs(workspace_id=workspace, limit=4),
            dispatch_ready=dispatch_ready,
        ),
    )

    top_signals = [
        item
        for item in briefing.get("top_signals", [])
        if isinstance(item, dict) and not is_bootstrap_signal(item)
    ]
    active_runs = [
        item for item in briefing.get("active_runs", []) if isinstance(item, dict)
    ]
    pending = int((briefing.get("pending_approvals") or {}).get("count") or 0)
    awaiting = int(briefing.get("awaiting_engagement_count") or 0)
    next_actions = [
        item for item in briefing.get("next_safe_actions", []) if isinstance(item, dict)
    ]

    fingerprint_payload = {
        "workspace_id": scoped,
        "pending": pending,
        "awaiting": awaiting,
        "dispatch_ready": dispatch_ready,
        "failed_employee_ids": [
            str(row.get("employee_id") or "").strip()
            for row in roster["failed"]
            if str(row.get("employee_id") or "").strip()
        ],
        "active_run_ids": [
            str(item.get("run_id") or "").strip()
            for item in active_runs
            if str(item.get("run_id") or "").strip()
        ],
        "busy_employee_ids": [
            str(row.get("employee_id") or "").strip()
            for row in roster["busy"]
            if str(row.get("employee_id") or "").strip()
        ],
        "handoff_receipt_ids": [
            str(row.get("receipt_id") or "").strip()
            for row in handoffs
            if str(row.get("receipt_id") or "").strip()
        ],
        "workspace_reports": fingerprint_rows(workspace_reports),
        "notice": str(briefing.get("notice") or "").strip(),
        "advise": str(briefing.get("advise") or "").strip(),
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()[:24]

    return {
        "workspace_id": scoped,
        "briefing": briefing,
        "fleet": fleet,
        "roster": roster,
        "handoffs": handoffs,
        "top_signals": top_signals,
        "active_runs": active_runs,
        "pending_approvals": pending,
        "awaiting_engagement_count": awaiting,
        "next_safe_actions": next_actions,
        "workspace_reports": workspace_reports,
        "fingerprint": fingerprint,
    }


def _attention_bits(snapshot: dict[str, Any]) -> list[str]:
    bits: list[str] = []
    pending = int(snapshot.get("pending_approvals") or 0)
    if pending > 0:
        noun = "approval" if pending == 1 else "approvals"
        bits.append(f"{_spell_count(pending)} {noun} waiting for your yes or no")

    awaiting = int(snapshot.get("awaiting_engagement_count") or 0)
    if awaiting > 0:
        if awaiting == 1:
            bits.append("a Lead-team plan waiting for you")
        else:
            bits.append(
                f"Lead-team plans waiting for you — {_spell_count(awaiting)} of them"
            )

    notice = str((snapshot.get("briefing") or {}).get("notice") or "").strip().rstrip(".")
    if notice:
        notice_l = notice.lower()
        # Avoid repeating the same awaiting-engagement beat from briefing notice.
        if "lead team plan" not in notice_l and "lead-team plan" not in notice_l and "waiting for you to engage" not in notice_l:
            bits.append(_scrub_operator_line(notice, max_len=180))

    for row in (snapshot.get("roster") or {}).get("failed") or []:
        bits.append(f"{_name_role(row)} last job failed")

    for signal in (snapshot.get("top_signals") or [])[:2]:
        title = str(signal.get("title") or "").strip()
        if title:
            severity = str(signal.get("severity") or "").strip().lower()
            if severity in {"high", "critical"}:
                bits.append(f"the loud one is {title}")
            else:
                bits.append(f"inbox is waving {title}")

    if _remote_ingress_soft(snapshot):
        reason = _degraded_reasons(snapshot)
        detail = _scrub_operator_line(reason[0], max_len=72) if reason else ""
        if detail:
            bits.append(f"public tunnel is soft ({detail}) — I can restart it")
        else:
            bits.append("public tunnel is soft — I can restart it from here")
    elif (snapshot.get("briefing") or {}).get("degraded", {}).get("active"):
        bits.append("local runtime is degraded — check connectivity before new work")
    return bits[:5]


def _work_bits(snapshot: dict[str, Any]) -> list[str]:
    bits: list[str] = []
    seen: set[str] = set()
    busy_labels: set[str] = set()
    for row in (snapshot.get("roster") or {}).get("busy") or []:
        label = _name_role(row)
        busy_labels.add(label.lower())
        status = str(row.get("status") or "busy").replace("_", " ")
        line = f"{label} is {status}"
        if line not in seen:
            seen.add(line)
            bits.append(line)

    for run in (snapshot.get("active_runs") or [])[:3]:
        summary = str(run.get("summary") or run.get("goal") or run.get("run_id") or "").strip()
        phase = str(run.get("phase") or "").replace("_", " ").strip()
        if not summary:
            continue
        line = f"{_truncate(summary, max_len=120)} is {phase}" if phase else _truncate(summary, max_len=140)
        if line not in seen:
            seen.add(line)
            bits.append(line)

    for row in (snapshot.get("roster") or {}).get("completed") or []:
        label = _name_role(row)
        if label.lower() in busy_labels:
            continue
        line = f"{label} just completed"
        if line not in seen:
            seen.add(line)
            bits.append(line)
    return bits[:6]


def _primary_lead_name(snapshot: dict[str, Any]) -> str:
    roster = snapshot.get("roster") or {}
    for row in roster.get("employees") or []:
        if not isinstance(row, dict):
            continue
        role = str(row.get("role") or row.get("role_label") or "").strip().lower()
        if bool(row.get("primary")) or role == "lead":
            name = str(row.get("name") or "").strip()
            if name:
                return name
    return "Lead"


def _lead_rollup_bits(snapshot: dict[str, Any]) -> list[str]:
    bits: list[str] = []
    seen: set[str] = set()
    dispatch_ready = _cli_dispatch_ready(snapshot)
    handoffs = _fresh_handoffs(
        [row for row in (snapshot.get("handoffs") or []) if isinstance(row, dict)],
        dispatch_ready=dispatch_ready,
    )
    for handoff in handoffs:
        lead_name = _scrub_operator_line(
            str(handoff.get("lead_name") or handoff.get("from_name") or ""),
            max_len=40,
        ) or _primary_lead_name(snapshot)
        raw_headline = str(handoff.get("headline") or "")
        raw_lead_next = str(handoff.get("lead_next") or "")
        # Preserve the verified Lead response for the board. Spoken narration
        # performs its own shorter projection; the visual transcript must not
        # silently cut receipts or conclusions.
        headline = _scrub_operator_line(raw_headline, max_len=420)
        lead_next = _scrub_operator_line(raw_lead_next, max_len=320)
        if not headline:
            continue
        if lead_next and lead_next.lower() not in headline.lower():
            line = f"{lead_name}: {headline}. Plan: {lead_next}"
        else:
            line = f"{lead_name}: {headline}"
        if line in seen:
            continue
        seen.add(line)
        bits.append(line)
    if bits:
        return bits[:3]

    # No verified handoff yet — Lead still briefs issue + fix intent from live board.
    lead_name = _primary_lead_name(snapshot)
    for row in (snapshot.get("roster") or {}).get("failed") or []:
        label = _name_role(row)
        line = (
            f"{lead_name}: {label} failed. "
            "Issue is the last shift outcome. "
            "Plan: diagnose the failure, then requeue the smallest fix."
        )
        if line not in seen:
            seen.add(line)
            bits.append(line)
    for signal in (snapshot.get("top_signals") or [])[:2]:
        if not isinstance(signal, dict):
            continue
        title = _scrub_operator_line(str(signal.get("title") or ""), max_len=80)
        summary = _scrub_operator_line(str(signal.get("summary") or ""), max_len=100)
        if not title:
            continue
        issue = summary or "needs containment"
        line = (
            f"{lead_name}: {title}. "
            f"Issue: {issue}. "
            "Plan: open Attention, contain blast radius, then land the smallest fix."
        )
        if line not in seen:
            seen.add(line)
            bits.append(line)
    if not bits and int(snapshot.get("awaiting_engagement_count") or 0) > 0:
        bits.append(
            f"{lead_name}: Lead-team plans are waiting. "
            "Issue: engagement gate is open. "
            "Plan: walk the rollup and decide the next handoff."
        )
    if not bits:
        bits.append(f"{lead_name}: No verified rollup yet — standing by on the board.")
    return bits[:5]


def _fleet_bits(snapshot: dict[str, Any]) -> list[str]:
    fleet = snapshot.get("fleet") or {}
    total = int(fleet.get("workspace_count") or fleet.get("count") or 0)
    critical = int(fleet.get("critical_count") or 0)
    attention = int(fleet.get("attention_count") or 0)
    bits: list[str] = []
    if critical > 0:
        bits.append(f"{_spell_count(critical)} workspace{'s' if critical != 1 else ''} critical")
    if attention > 0:
        bits.append(
            f"{_spell_count(attention)} workspace{'s' if attention != 1 else ''} need attention"
        )
    if not bits and total > 0:
        bits.append(f"fleet looks nominal across {_spell_count(total)} workspace{'s' if total != 1 else ''}")
    elif not bits:
        bits.append("fleet telemetry quiet from here")
    return bits[:3]


def compose_operator_report(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Compose fixed-section REPORT text from a snapshot."""
    attention = _attention_bits(snapshot)
    work = _work_bits(snapshot)
    reports = [row for row in snapshot.get("workspace_reports") or [] if isinstance(row, dict)]
    workspace_updates = workspace_update_bits(reports, _spell_count)
    rollups = fleet_lead_rollup_bits(snapshot, reports, _lead_rollup_bits) or _lead_rollup_bits(snapshot)
    fleet = _fleet_bits(snapshot)
    nxt = _next_move(snapshot)

    sections = {
        "attention": attention,
        "work_in_flight": work,
        "workspace_updates": workspace_updates,
        "lead_rollups": rollups,
        "fleet": fleet,
        "next_move": nxt,
    }

    text, spoken = render_report_text(
        snapshot=snapshot, attention=attention, work=work,
        workspace_updates=workspace_updates, rollups=rollups, fleet=fleet,
        next_move=nxt, spell_count=_spell_count,
    )

    return {
        "text": text,
        "spoken": spoken,
        "sections": sections,
        "fingerprint": snapshot.get("fingerprint"),
        "lane": "deterministic_report",
    }
__all__ = ["build_operator_report_snapshot", "compose_operator_report", "is_operator_report_request"]
