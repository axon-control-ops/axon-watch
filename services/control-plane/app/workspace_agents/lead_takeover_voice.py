"""Spoken Lead rollups — broadcast TTS lines after takeover / synthesis posts."""

from __future__ import annotations

import logging
from typing import Any

from app.workspace_agents.lead_text import (
    lead_summary_from_reply,
    strip_confidence_lines,
    truncate_text,
)

logger = logging.getLogger(__name__)


def _lead_speaker(workspace_id: str) -> dict[str, str]:
    from app.workspace_agents.lead_fan_out import employee_for_role

    employee = employee_for_role(workspace_id, "lead") or {}
    name = str(employee.get("name") or "Lead").strip() or "Lead"
    employee_id = str(employee.get("employee_id") or "").strip()
    return {
        "speaker_name": name,
        "speaker_role": "lead",
        "speaker_employee_id": employee_id,
    }


def build_lead_takeover_spoken_line(
    *,
    employee_name: str,
    employee_role: str,
    phase: str,
    reply_text: str | None,
    lead_name: str = "Lead",
    parent_plan_goal: str | None = None,
) -> str:
    """TTS-friendly executive brief without runtime protocol or shell chores."""
    from app.workspace_agents.lead_executive_brief import (
        compress_ask,
        executive_next_step,
        executive_operator_action,
        plain_outcome,
    )
    from app.workspace_agents.lead_takeover import extract_lead_next

    name = (employee_name or employee_role or "specialist").strip()
    role = (employee_role or "specialist").strip()
    status = "completed" if phase == "completed" else (phase or "ended")
    lead = (lead_name or "Lead").strip() or "Lead"
    parent_ask = compress_ask(parent_plan_goal)
    outcome = plain_outcome(reply_text)
    lead_next = extract_lead_next(reply_text)
    parts = [f"{lead} here."]
    if parent_ask:
        suffix = "" if parent_ask.endswith((".", "!", "?")) else "."
        parts.append(f"Goal: {parent_ask}{suffix}")
    else:
        parts.append("Goal: Complete the requested result and verify that it is ready to use.")
    progress = outcome or "no verified result is available yet."
    if not progress.endswith((".", "!", "?")):
        progress = f"{progress}."
    parts.append(f"Progress: {name} ({role}) {status}; {progress}")
    parts.append("What remains: The requested result must be verified and ready to use.")
    parts.append(
        "What I am doing next: "
        + executive_next_step(
            lead_next=lead_next,
            specialist_name=name,
            parent_ask=parent_ask,
            status=status,
        )
    )
    parts.append("Your action: " + executive_operator_action(lead_next))
    # Each part above already ends with terminal punctuation, so joining on a
    # single space still reads as separate sentences both spoken and on-screen
    # (this line also drives the visible VAXON transmission text, not just TTS
    # — see useSpokenUtteranceText.ts).
    return " ".join(parts)


def build_lead_synthesis_spoken_line(
    *,
    goal: str,
    summary: str,
    findings: list[dict[str, Any]],
    lead_name: str = "Lead",
) -> str:
    lead = (lead_name or "Lead").strip() or "Lead"
    goal_line = truncate_text(goal, max_len=160) or "Lead plan"
    parts = [
        f"{lead} here — team rollup is ready.",
        f"Goal: {goal_line}.",
    ]
    clean_summary = truncate_text(strip_confidence_lines(summary), max_len=240)
    if clean_summary:
        parts.append(f"Outcome: {clean_summary}")
    bits: list[str] = []
    for row in findings[:5]:
        owner = str(row.get("assignee_name") or row.get("owner_role") or "specialist").strip()
        status = str(row.get("status") or "unknown").strip()
        excerpt = truncate_text(
            strip_confidence_lines(str(row.get("specialist_reply_excerpt") or "")),
            max_len=120,
        )
        bit = f"{owner} {status}"
        if excerpt:
            bit = f"{bit}: {excerpt}"
        bits.append(bit)
    if bits:
        parts.append("Specialists: " + "; ".join(bits) + ".")
    parts.append(
        "Next: I will turn this rollup into the next assignment and only "
        "escalate a real decision gate."
    )
    return " ".join(parts)


def build_lead_shift_spoken_line(
    *,
    employee_name: str,
    phase: str,
    reply_text: str | None,
) -> str:
    from app.workspace_agents.lead_takeover import extract_lead_next

    name = (employee_name or "Lead").strip() or "Lead"
    status = "completed" if phase == "completed" else (phase or "ended")
    summary = lead_summary_from_reply(reply_text)
    lead_next = extract_lead_next(reply_text)
    parts = [f"{name} here. My Lead shift just {status}."]
    if summary:
        parts.append(f"Report: {summary}")
    if lead_next:
        parts.append(f"Next: {lead_next}")
    else:
        parts.append("Next: I will keep owning the plan and only escalate real gates.")
    return " ".join(parts)


def emit_lead_spoken_line(
    *,
    workspace_id: str,
    line: str,
    receipt_id: str,
    kind: str = "lead_takeover",
) -> dict[str, Any]:
    """Broadcast a spoken_line live event for the console voice queue."""
    cleaned = " ".join(str(line or "").strip().split())
    if not cleaned:
        return {"status": "skipped_empty"}
    speaker = _lead_speaker(workspace_id)
    try:
        from app.live_events import broadcast_spoken_line

        delivered = broadcast_spoken_line(
            line=cleaned,
            receipt_id=receipt_id,
            workspace_id=workspace_id,
            kind=kind,
            speaker_name=speaker["speaker_name"],
            speaker_role=speaker["speaker_role"],
            speaker_employee_id=speaker["speaker_employee_id"] or None,
        )
    except Exception as exc:  # noqa: BLE001 — voice must not fail Lead posting
        logger.warning("lead spoken_line broadcast failed (%s): %s", kind, exc)
        return {"status": "error", "detail": str(exc)}
    return {
        "status": "broadcast",
        "delivered": delivered,
        "kind": kind,
        "receipt_id": receipt_id,
        **speaker,
    }


def emit_lead_shift_spoken(
    *,
    workspace_id: str,
    run_id: str,
    employee_name: str,
    phase: str,
    reply_text: str | None,
) -> dict[str, Any]:
    """Build + broadcast Lead-shift TTS (shrinks call-site in vaxon handoff)."""
    return emit_lead_spoken_line(
        workspace_id=workspace_id,
        line=build_lead_shift_spoken_line(
            employee_name=employee_name,
            phase=phase,
            reply_text=reply_text,
        ),
        receipt_id=f"lead_shift_voice_{run_id}",
        kind="lead_shift",
    )


__all__ = [
    "build_lead_shift_spoken_line",
    "build_lead_synthesis_spoken_line",
    "build_lead_takeover_spoken_line",
    "emit_lead_shift_spoken",
    "emit_lead_spoken_line",
]
