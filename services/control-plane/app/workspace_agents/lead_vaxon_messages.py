"""VAXON operator-thread message builders for Lead handoffs."""

from __future__ import annotations

from typing import Any

from app.workspace_agents.lead_text import truncate_text


def build_lead_synthesis_vaxon_message(
    *,
    plan_id: str,
    goal: str,
    summary: str,
    findings: list[dict[str, Any]],
) -> str:
    """Build one operator-facing VAXON rollup (no PII invention)."""
    goal_line = truncate_text(goal, max_len=280) or "Lead plan"
    lines = [
        "VAXON: Lead team rollup is ready for your review.",
        f"Goal: {goal_line}",
        f"Plan: {plan_id}",
    ]
    clean_summary = truncate_text(summary, max_len=500)
    if clean_summary:
        lines.append(f"Outcome: {clean_summary}")

    for row in findings[:8]:
        owner = str(row.get("assignee_name") or row.get("owner_role") or "specialist").strip()
        status = str(row.get("status") or "").strip() or "unknown"
        outcome = truncate_text(str(row.get("outcome") or ""), max_len=160)
        excerpt = truncate_text(str(row.get("specialist_reply_excerpt") or ""), max_len=160)
        run_ids = [str(item).strip() for item in (row.get("run_ids") or []) if str(item).strip()]
        run_bit = f" · runs {', '.join(run_ids[:3])}" if run_ids else ""
        detail = f"{owner}: {status}"
        if outcome:
            detail = f"{detail} ({outcome})"
        if excerpt:
            detail = f"{detail} — {excerpt}"
        lines.append(f"- {detail}{run_bit}")

    lines.append("Open Dana's Lead thread for the full narrative, or ask me what to do next.")
    # No trailing Confidence boilerplate: this is a deterministic rollup, not
    # an LLM turn — there's no model self-assessment to score (see
    # lead_team_checkin.py's identical reasoning for the check-in message).
    return "\n".join(lines)


def build_ad_hoc_lead_vaxon_message(
    *,
    workspace_id: str,
    employee_name: str,
    employee_role: str,
    phase: str,
    run_id: str,
    lead_next: str = "",
    lead_summary: str = "",
) -> str:
    """Short operator-thread flash from a Lead-verified ad-hoc synthesis."""
    name = (employee_name or employee_role or "specialist").strip()
    role = (employee_role or "specialist").strip()
    status = "completed" if phase == "completed" else (phase or "ended")
    lines = [
        f"VAXON: {name} ({role}) just {status}.",
        f"Workspace: {workspace_id}",
        f"Run: {run_id}",
    ]
    if role.lower() == "lead":
        lines.append("Lead shift rollup is ready in the Lead tab.")
    else:
        lines.append("Lead has the takeover rollup in their Lead tab.")
    summary = truncate_text(lead_summary, max_len=280)
    if summary:
        lines.append(f"Lead summary: {summary}")
    next_line = truncate_text(lead_next, max_len=220)
    if next_line:
        lines.append(f"Lead next: {next_line}")
    lines.append(
        "Ask me REPORT / update anytime — I keep fleet state from Lead handoffs."
    )
    return "\n".join(lines)


__all__ = [
    "build_ad_hoc_lead_vaxon_message",
    "build_lead_synthesis_vaxon_message",
]
