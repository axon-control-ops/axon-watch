"""Authoritative company team roster for employee / Lead prompts.

Leads must not Glob/Grep the repo to learn names, roles, or owns — the control
plane already has the roster. Inject that knowledge into every Lead (and
specialist handoff) prompt.
"""

from __future__ import annotations

from typing import Any

TEAM_ROSTER_MARKER = (
    "Company team roster (authoritative — do not search the repo for this):"
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _format_employee_line(row: dict[str, Any], *, detail: bool) -> str:
    name = _clean(row.get("name")) or "Teammate"
    role = _clean(row.get("role")) or "workspace_agent"
    role_label = _clean(row.get("role_label")) or role
    owns = _clean(row.get("owns")) or "assigned workspace work"
    schedule = _clean(row.get("schedule"))
    status = _clean(row.get("status"))
    employee_id = _clean(row.get("employee_id"))
    enabled = row.get("enabled")
    primary = bool(row.get("primary"))
    last_outcome = _clean(row.get("last_outcome")).lower()
    last_detail = _clean(row.get("last_outcome_detail"))

    bits = [f"- {name} ({role_label} / {role})"]
    if primary or role == "lead":
        bits.append(" [LEAD]")
    if enabled is False:
        bits.append(" [disabled]")
    bits.append(f" — owns: {owns}")
    if detail:
        if schedule:
            bits.append(f"; schedule: {schedule}")
        if status:
            bits.append(f"; status: {status}")
        if employee_id:
            bits.append(f"; id: {employee_id}")
        if last_outcome == "failed" and last_detail:
            from app.workspace_agents.failure_detail import (
                is_billing_block_failure,
                is_usage_limit_failure,
                normalize_operator_failure_detail,
            )

            cleaned_detail = normalize_operator_failure_detail(last_detail)
            if is_billing_block_failure(cleaned_detail):
                bits.append(
                    "; last job failed: Cursor unpaid invoice "
                    "(pay invoice at cursor.com/dashboard — not a code-repair task)"
                )
            elif is_usage_limit_failure(cleaned_detail):
                bits.append(
                    "; last job failed: Cursor usage signal "
                    "(do not claim teammates are account-wide exhausted — "
                    "check live Auto+Composer vs API pools)"
                )
            else:
                bits.append(f"; last job failed: {cleaned_detail or last_detail}")
        elif last_outcome:
            bits.append(f"; last outcome: {last_outcome}")
            if last_detail:
                bits.append(f" ({last_detail})")
    return "".join(bits)


def format_team_roster_block(
    company: dict[str, Any] | None,
    *,
    viewer_role: str | None = None,
) -> str:
    """Format a company roster dict into an authoritative prompt block."""
    if not isinstance(company, dict):
        return ""
    employees = company.get("employees")
    if not isinstance(employees, list) or not employees:
        return ""

    workspace_id = _clean(company.get("workspace_id")) or "workspace"
    company_name = _clean(company.get("company_name")) or workspace_id
    role = _clean(viewer_role).lower()
    # Leads get full operational detail; specialists get enough for handoffs.
    detail = role in {"", "lead"}

    lines: list[str] = [
        TEAM_ROSTER_MARKER,
        f"Company: {company_name} ({workspace_id}). "
        f"Headcount: {len(employees)}.",
    ]
    for row in employees:
        if isinstance(row, dict):
            lines.append(_format_employee_line(row, detail=detail))

    if detail:
        lines.append(
            "Use this roster for planning, delegation, status, and handoffs. "
            "Do NOT Glob, Grep, or Read the filesystem to discover teammates, "
            "roles, owns, or staffing — this block is the source of truth. "
            "If someone is missing, disabled, or failed here, say so from this "
            "block rather than searching docs or agent reports."
        )
    else:
        lines.append(
            "Use this roster only for handoffs and role boundaries. "
            "Do not search the repo to rediscover teammates."
        )
    return "\n".join(lines)


def build_team_roster_context(
    workspace_id: str,
    *,
    viewer_role: str | None = None,
) -> str:
    """Load the live company roster and format it for prompts."""
    cleaned = _clean(workspace_id)
    if not cleaned:
        return ""
    # Local import keeps prompt helpers usable in unit tests without full roster I/O.
    from app.workspace_agents import build_company_roster

    try:
        company = build_company_roster(cleaned)
    except Exception:
        return ""
    return format_team_roster_block(company, viewer_role=viewer_role)
