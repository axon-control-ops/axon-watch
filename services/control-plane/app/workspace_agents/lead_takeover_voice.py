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
) -> str:
    """TTS-friendly Lead takeover — specialist excerpt + Lead read + next."""
    name = (employee_name or employee_role or "specialist").strip()
    role = (employee_role or "specialist").strip()
    status = "completed" if phase == "completed" else (phase or "ended")
    lead = (lead_name or "Lead").strip() or "Lead"
    from app.workspace_agents.lead_takeover import extract_lead_next

    excerpt = truncate_text(strip_confidence_lines(reply_text), max_len=320)
    lead_next = extract_lead_next(reply_text)
    parts = [
        f"{lead} here. {name} ({role}) just {status}.",
    ]
    if excerpt:
        parts.append(f"Specialist report: {excerpt}")
    if status == "completed":
        parts.append(
            f"My read: {name} finished their slice. I own the handoff — "
            "cross-team decisions stay with me until you Decide."
        )
    else:
        parts.append(
            f"My read: {name}'s job {status}. I will triage blockers and reassign if needed."
        )
    if lead_next:
        parts.append(f"Lead next: {lead_next}")
    else:
        parts.append(
            "Lead next: review their report, confirm any Decide gates, then assign or approve."
        )
    parts.append("Open my Lead tab for the full rollup. Ask me what to do next.")
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
    parts.append("Open my Lead tab for the full narrative, or ask me what to do next.")
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
        parts.append(f"Lead next: {lead_next}")
    parts.append("Ask me what to do next.")
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
