"""Deterministic operator REPORT lane — roster + briefing + verified handoffs.

Never invokes Lane B / IDE Composer. Never repeats raw specialist transcripts.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.kairo.report_text import (
    _scrub_operator_line,
    _truncate,
    push_failure_next_move,
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

_REPORT_HOTWORD_RE = re.compile(
    r"^(?:report|status(?:\s+report)?|update|stand[\s-]?up|"
    r"where\s+do\s+we\s+stand|where\s+are\s+we(?:\s+now)?|"
    r"what(?:'?s| is)\s+(?:going\s+on|happening))\s*[.!]?\s*$",
    re.IGNORECASE,
)

# Fleet stand-up phrases — avoid matching "report back when done" completion asks.
_REPORT_PHRASE_RE = re.compile(
    r"\b("
    r"status report|"
    r"stand[\s-]?up|"
    r"where things stand|"
    r"where do we stand|"
    r"roll.?up|"
    r"brief(?:ing)? me|"
    r"jarvis-style second-brain stand-up|"
    r"what each teammate|"
    r"team status|"
    r"single best next move|"
    r"work in flight|"
    r"lead rollups?"
    r")\b",
    re.IGNORECASE,
)

# Bare "report" only when it is the ask — not "report back", "reporting", etc.
_REPORT_WORD_ASK_RE = re.compile(
    r"(?:^|[—\-,:;]\s*)report(?:\s*[—\-:]|\s+on\b|\s*$)",
    re.IGNORECASE,
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


def is_operator_report_request(content: str) -> bool:
    """True when the operator asked for a fleet stand-up / REPORT."""
    trimmed = str(content or "").strip()
    if not trimmed:
        return False
    if _REPORT_HOTWORD_RE.match(trimmed):
        return True
    lower = trimmed.lower()
    # Completion instructions ("handle X and report back") are not stand-ups.
    if re.search(r"\breport\s+back\b", lower):
        return False
    if lower.startswith("report —") or lower.startswith("report -"):
        return True
    if _REPORT_PHRASE_RE.search(trimmed):
        return True
    return bool(_REPORT_WORD_ASK_RE.search(trimmed))


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

    scoped = str(workspace_id or "").strip() or str(
        (briefing.get("scope") or {}).get("workspace_id") or ""
    ).strip()
    dispatch_ready = _cli_dispatch_ready(briefing=briefing)
    roster = _roster_snapshot(scoped or None, dispatch_ready=dispatch_ready)
    handoffs = _fresh_handoffs(
        list_verified_lead_handoffs(workspace_id=scoped or None, limit=8),
        dispatch_ready=dispatch_ready,
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
        "fingerprint": fingerprint,
    }


def _degraded_reasons(snapshot: dict[str, Any]) -> list[str]:
    degraded = (snapshot.get("briefing") or {}).get("degraded") or {}
    if not isinstance(degraded, dict):
        return []
    raw = degraded.get("reasons") or []
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _remote_ingress_soft(snapshot: dict[str, Any]) -> bool:
    degraded = (snapshot.get("briefing") or {}).get("degraded") or {}
    if not isinstance(degraded, dict) or not degraded.get("active"):
        return False
    joined = " ".join(_degraded_reasons(snapshot)).lower()
    if not joined:
        # Legacy briefings sometimes mark degraded without reasons — keep prior soft-tunnel copy.
        return True
    markers = (
        "tunnel",
        "remote ingress",
        "edudashpro",
        "public health",
        "network unreachable",
        "host unreachable",
        "name or service not known",
    )
    return any(marker in joined for marker in markers)


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
    total = int(fleet.get("workspace_count") or 0)
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


def _handoff_push_failure_next_move(snapshot: dict[str, Any]) -> str | None:
    for handoff in snapshot.get("handoffs") or []:
        if not isinstance(handoff, dict):
            continue
        raw = " ".join(
            [
                str(handoff.get("headline") or ""),
                str(handoff.get("lead_summary") or ""),
                str(handoff.get("lead_next") or ""),
            ]
        )
        next_move = push_failure_next_move(raw)
        if next_move:
            return next_move
    return None


def _signal_next_move(snapshot: dict[str, Any]) -> str | None:
    """Prefer a concrete next move from the loudest open signal."""
    for signal in (snapshot.get("top_signals") or [])[:3]:
        if not isinstance(signal, dict):
            continue
        title = str(signal.get("title") or "").strip()
        summary = str(signal.get("summary") or "").strip()
        hay = f"{title} {summary}".lower()
        if not title:
            continue
        if "github" in hay and (
            "token" in hay
            or "401" in hay
            or "placeholder" in hay
            or "probe" in hay
            or "api warning" in hay
        ):
            return "I'll open Vault and restore the GitHub probe token next"
        if "sentry" in hay:
            return f"I'll open Attention for {title}"
        severity = str(signal.get("severity") or "").strip().lower()
        if severity in {"critical", "high"}:
            return f"I'll open Attention for {title}"
    return None


def _next_move(snapshot: dict[str, Any]) -> str:
    pending = int(snapshot.get("pending_approvals") or 0)
    if pending > 0:
        return "I'll clear Approvals before starting anything new"

    if _remote_ingress_soft(snapshot):
        return "I'll restart the public tunnel next"

    # A verified push receipt beats stale fleet advice, but recovery must follow
    # the actual stderr rather than guessing auth / branch protection.
    push_next_move = _handoff_push_failure_next_move(snapshot)
    if push_next_move:
        return push_next_move

    signal_move = _signal_next_move(snapshot)
    if signal_move:
        return signal_move

    advise = str((snapshot.get("briefing") or {}).get("advise") or "").strip().rstrip(".")
    if advise:
        advise_clean = _scrub_operator_line(advise, max_len=160)
        lower = advise_clean.lower()
        if lower.startswith(("i'd", "i'll", "i will")):
            return advise_clean
        if "needs review" in lower and "switch" in lower:
            target = re.search(r"\bsignal in ([a-z0-9_-]+)\b", advise_clean, re.IGNORECASE)
            return (
                f"I'll switch to {target.group(1)} and start that investigation next"
                if target
                else "I'll switch us there and start that investigation next"
            )
        if "github" in lower and ("token" in lower or "vault" in lower or "api" in lower):
            return "I'll open Vault and restore the GitHub probe token next"
        if "lead" in lower and ("rollup" in lower or "open" in lower):
            return "I'll open the Lead rollup and walk the next handoff"
        if "approval" in lower:
            return "I'll clear Approvals before starting anything new"
        if "tunnel" in lower or "remote ingress" in lower or "public health" in lower:
            return "I'll restart the public tunnel next"
        if lower.startswith("inspect "):
            target = advise_clean[8:].strip() or "that signal"
            return f"I'll open Attention for {target}"
        if "sentry" in lower:
            return f"I'll open Attention for {advise_clean}"
        return f"I'll open Attention for {advise_clean}"
    for handoff in snapshot.get("handoffs") or []:
        lead_next = _scrub_operator_line(str(handoff.get("lead_next") or ""), max_len=140)
        if lead_next:
            return f"I'll take the next Lead decision: {lead_next}"
    awaiting = int(snapshot.get("awaiting_engagement_count") or 0)
    if awaiting > 0:
        return "I'll open Mission Control for the Lead rollup"
    actions = snapshot.get("next_safe_actions") or []
    if actions:
        label = str(actions[0].get("label") or actions[0].get("title") or "").strip()
        if label:
            return f"I'll {label[0].lower() + label[1:]}" if label[0].isupper() else f"I'll {label}"
    return "I'll keep watching — say the word if you want DashPro, Approvals, or a fleet roll"


def compose_operator_report(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Compose fixed-section REPORT text from a snapshot."""
    attention = _attention_bits(snapshot)
    work = _work_bits(snapshot)
    rollups = _lead_rollup_bits(snapshot)
    fleet = _fleet_bits(snapshot)
    nxt = _next_move(snapshot)

    sections = {
        "attention": attention,
        "work_in_flight": work,
        "lead_rollups": rollups,
        "fleet": fleet,
        "next_move": nxt,
    }

    if not attention and not work and not rollups:
        text = (
            "Here's the stand-up. Attention: nothing screaming. "
            "Work in flight: idle. "
            f"Fleet: {', '.join(fleet)}. "
            f"Next move: {nxt}."
        )
    else:
        parts = [
            "Here's the stand-up.",
            f"Attention: {', '.join(attention) if attention else 'nothing screaming'}.",
            f"Work in flight: {', '.join(work) if work else 'idle'}.",
        ]
        if rollups:
            parts.append(f"Lead rollups: {'; '.join(rollups)}.")
        else:
            parts.append("Lead rollups: none verified yet.")
        parts.append(f"Fleet: {', '.join(fleet)}.")
        parts.append(f"Next move: {nxt}.")
        text = " ".join(parts)

    return {
        "text": text,
        "spoken": text,
        "sections": sections,
        "fingerprint": snapshot.get("fingerprint"),
        "lane": "deterministic_report",
    }
__all__ = ["build_operator_report_snapshot", "compose_operator_report", "is_operator_report_request"]
