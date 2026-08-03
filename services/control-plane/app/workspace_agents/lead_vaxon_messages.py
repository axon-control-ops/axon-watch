"""VAXON operator-thread message builders for Lead handoffs."""

from __future__ import annotations

from typing import Any

from app.workspace_agents.lead_text import sentence_text, truncate_text


def build_lead_synthesis_vaxon_message(
    *,
    plan_id: str,
    goal: str,
    summary: str,
    findings: list[dict[str, Any]],
) -> str:
    """Build one concise operator-facing VAXON rollup (no PII invention)."""
    goal_line = truncate_text(goal, max_len=280) or "Lead plan"
    lines = ["VAXON update — Lead rollup engaged.", f"Goal: {goal_line}"]

    completed = [row for row in findings if str(row.get("status") or "").strip() == "completed"]
    attention = [row for row in findings if str(row.get("status") or "").strip() != "completed"]
    if findings and not attention:
        lines.append(f"Outcome: all {len(completed)} specialist checks are complete.")
    elif findings:
        lines.append(
            f"Outcome: {len(completed)} complete; {len(attention)} need attention."
        )
    else:
        clean_summary = truncate_text(summary, max_len=280)
        if clean_summary:
            lines.append(f"Outcome: {sentence_text(clean_summary, max_len=280)}")

    # Completed work is represented in the outcome count. Show only the
    # exceptions so the operator sees the next decision without a duplicate
    # inventory of the entire team.
    for row in attention[:3]:
        owner = str(row.get("assignee_name") or row.get("owner_role") or "specialist").strip()
        status = str(row.get("status") or "").strip() or "unknown"
        outcome = truncate_text(str(row.get("outcome") or ""), max_len=160)
        excerpt = truncate_text(str(row.get("specialist_reply_excerpt") or ""), max_len=160)
        detail = f"Needs attention: {owner} ({status})"
        if outcome:
            detail = f"{detail} ({outcome})"
        if excerpt:
            detail = f"{detail} — {sentence_text(excerpt, max_len=160)}"
        lines.append(f"- {detail}")

    lines.append("Action taken: VAXON reviewed the rollup and routed it to Dana for the remaining gate.")
    lines.append("Next: Dana advances the gate or surfaces the one decision required.")
    lines.append("Confidence: 8/10")
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
    lines = [f"VAXON update — {name} ({role}) {status}."]
    if role.lower() == "lead":
        lines.append("Dana owns the next step.")
    else:
        lines.append("Dana has the handoff.")
    summary = truncate_text(lead_summary, max_len=280)
    if summary:
        lines.append(f"Outcome: {sentence_text(summary, max_len=280)}")
    next_line = truncate_text(lead_next, max_len=220)
    if next_line:
        lines.append(f"Next action: {sentence_text(next_line, max_len=220)}")
    else:
        lines.append("Next action: Dana is queued to verify the active plan and advance the next safe step.")
    lines.append("Confidence: 8/10")
    return "\n".join(lines)


__all__ = [
    "build_ad_hoc_lead_vaxon_message",
    "build_lead_synthesis_vaxon_message",
]
