"""Continuous Lead takeover after specialist shifts (plan-linked or ad-hoc IDE)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.persistence import chat_store
from app.workspace_agents.lead_checkin_assign import SPECIALIST_ROLES
from app.workspace_agents.lead_fan_out import _employee_id_for_role
from app.workspace_agents.lead_takeover_followup import enqueue_lead_follow_up_task
from app.workspace_agents.lead_text import (
    lead_summary_from_reply as _lead_summary_from_reply,
    sentence_text as _sentence,
    strip_thinking as _strip_thinking,
    truncate_text as _truncate,
)

logger = logging.getLogger(__name__)

_LEAD_NEXT_RE = re.compile(
    r"(?:blockers?\s*/\s*lead\s*next|lead\s*next|lead:)\s*[-–—:]?\s*(.+)",
    re.IGNORECASE,
)
_NEXT_ACTION_RE = re.compile(
    r"^(?:next\s+action|next\s+step|recommended\s+next\s+step)\s*[-–—:]?\s*(.+)$",
    re.IGNORECASE,
)


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _new_message_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def extract_lead_next(reply_text: str | None) -> str:
    body = _strip_thinking(reply_text or "")
    if len(body) > 4000:
        body = body[-4000:]
    # Prefer explicit Lead: decision lines from the specialist report.
    for line in body.splitlines():
        cleaned = line.strip().lstrip("-*• ").strip()
        if not cleaned:
            continue
        lead_match = re.match(r"^lead\s*:?\s*\*{0,2}\s*(.+)$", cleaned, flags=re.IGNORECASE)
        if lead_match:
            return _truncate(lead_match.group(1).strip().lstrip("*").strip(), max_len=280)
        next_action_match = _NEXT_ACTION_RE.match(cleaned)
        if next_action_match:
            return _truncate(next_action_match.group(1).strip().lstrip("*").strip(), max_len=280)
    match = _LEAD_NEXT_RE.search(body)
    if not match:
        return ""
    candidate = match.group(1).strip()
    # Inline "Blockers / Lead next: Lead: …" — peel nested Lead: prefix.
    nested = re.match(r"^lead\s*:?\s*\*{0,2}\s*(.+)$", candidate, flags=re.IGNORECASE)
    if nested:
        return _truncate(nested.group(1).strip().lstrip("*").strip(), max_len=280)
    return _truncate(candidate, max_len=280)


def extract_blockers(reply_text: str | None) -> str:
    """Capture specialist-authored blockers excluding the Lead decision line."""
    body = _strip_thinking(reply_text or "")
    if len(body) > 4000:
        body = body[-4000:]
    bits: list[str] = []
    in_blockers = False
    for line in body.splitlines():
        cleaned = line.strip().lstrip("-*• ").strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if "blockers" in lowered and ("lead next" in lowered or lowered.startswith("blockers")):
            in_blockers = True
            # Inline form: "Blockers / Lead next: Marco …"
            after = cleaned.split(":", 1)
            if len(after) == 2 and after[1].strip() and not after[1].strip().lower().startswith("lead:"):
                inline = after[1].strip()
                if not inline.lower().startswith("lead"):
                    bits.append(_truncate(inline, max_len=200))
            continue
        if in_blockers:
            if lowered.startswith("confidence:"):
                break
            if lowered.startswith("lead:"):
                continue
            bits.append(_truncate(cleaned, max_len=200))
    return _truncate("; ".join(bits), max_len=280)


def _ensure_lead_ide_thread(workspace_id: str) -> dict[str, Any] | None:
    employee_id = _employee_id_for_role(workspace_id, "lead")
    if not employee_id:
        return None
    created_at = _utc_now_iso()
    thread = chat_store.find_thread_for_employee(
        workspace_id,
        employee_id=employee_id,
        thread_kind="ide",
    )
    if thread is None:
        thread = chat_store.create_thread(
            workspace_id=workspace_id,
            run_id=None,
            created_at=created_at,
            thread_kind="ide",
            title="Lead · takeover",
            employee_id=employee_id,
            employee_role="lead",
        )
    return thread


def _already_posted_takeover(thread_id: str, run_id: str) -> bool:
    cleaned_run = str(run_id or "").strip()
    if not cleaned_run:
        return False
    try:
        history = chat_store.list_thread_messages(thread_id)
    except Exception:  # noqa: BLE001
        return False
    needle = f"Run: {cleaned_run}"
    recent = list(reversed(history or []))[:40]
    for message in recent:
        if str(message.get("role") or "") != "agent":
            continue
        content = str(message.get("content") or "")
        if needle in content and ("Lead takeover" in content or "Lead update" in content):
            return True
        if str(message.get("run_id") or "").strip() == cleaned_run and (
            "Lead takeover" in content or "Lead update" in content
        ):
            return True
    return False


def build_lead_takeover_message(
    *,
    employee_name: str,
    employee_role: str,
    phase: str,
    goal: str,
    outcome: str,
    reply_text: str | None,
    run_id: str,
    plan_id: str | None = None,
    task_id: str | None = None,
    parent_plan_goal: str | None = None,
) -> str:
    """Build the concise, directive Lead update shown in the Lead thread.

    The worker transcript and identifiers remain available through receipts. The
    operator-facing update is deliberately one screenful: outcome, the active
    goal, and the next action. Repeating the specialist's full account, parent
    goal, and a generic invitation to ask a question turned a useful handoff
    into noise.
    """
    name = (employee_name or employee_role or "specialist").strip()
    status = "completed" if phase == "completed" else (phase or "ended")
    summary = _lead_summary_from_reply(reply_text)
    lead_next = extract_lead_next(reply_text)
    parent_ask = _truncate(parent_plan_goal or "", max_len=240)
    goal_line = _truncate(goal, max_len=240)
    outcome_line = _truncate(outcome, max_len=200)

    lines = [f"Lead update — {name} {status}."]
    active_goal = parent_ask or goal_line
    if active_goal:
        lines.append(f"Goal: {active_goal}")
    if summary:
        lines.append(f"Outcome: {_sentence(summary)}")
    elif outcome_line:
        lines.append(f"Outcome: {_sentence(outcome_line)}")

    if lead_next:
        lines.append(f"Next action: {_sentence(lead_next)}")
    elif status == "completed":
        lines.append("Next action: I will verify the remaining gate and advance only the unfinished work.")
    else:
        lines.append("Next action: I will isolate the blocker, then reassign or escalate it.")
    lines.append("Confidence: 8/10")
    return "\n".join(lines)


def post_lead_takeover_report(
    *,
    workspace_id: str,
    run_id: str,
    employee_role: str,
    employee_name: str,
    phase: str,
    goal: str = "",
    outcome: str = "",
    reply_text: str | None = None,
    plan_id: str | None = None,
    task_id: str | None = None,
    create_follow_up_task: bool = True,
) -> dict[str, Any]:
    """Always post a Dana/Lead IDE takeover when a specialist shift ends."""
    role = str(employee_role or "").strip().lower()
    if role not in SPECIALIST_ROLES:
        return {"status": "skipped_not_specialist", "employee_role": role}
    cleaned_run = str(run_id or "").strip()
    if not cleaned_run:
        return {"status": "skipped_missing_run"}

    thread = _ensure_lead_ide_thread(workspace_id)
    if thread is None:
        return {"status": "skipped_no_lead"}
    thread_id = str(thread["thread_id"])
    if _already_posted_takeover(thread_id, cleaned_run):
        # Takeover is idempotent, but a missing VAXON receipt can still be filled
        # from Lead-verified fields without duplicating Dana's message or follow-up.
        vaxon_flash: dict[str, Any] | None = None
        try:
            from app.workspace_agents.lead_vaxon_handoff import post_ad_hoc_lead_takeover_to_vaxon

            vaxon_flash = post_ad_hoc_lead_takeover_to_vaxon(
                workspace_id=workspace_id,
                run_id=cleaned_run,
                employee_role=role,
                employee_name=employee_name,
                phase=phase if phase in {"completed", "failed"} else phase,
                lead_next=extract_lead_next(reply_text),
                lead_summary=_lead_summary_from_reply(reply_text),
                lead_thread_id=thread_id,
                blockers=extract_blockers(reply_text),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("ad-hoc VAXON takeover flash (already_posted path) failed: %s", exc)
            vaxon_flash = {"status": "error", "detail": str(exc)}
        return {
            "status": "already_posted",
            "thread_id": thread_id,
            "run_id": cleaned_run,
            "vaxon_flash": vaxon_flash,
        }

    from app.workspace_agents.lead_plan_control import controlling_lead_plan

    controlling = controlling_lead_plan(
        workspace_id,
        plan_id=plan_id,
        task_id=task_id,
    )
    resolved_plan_id = str((controlling or {}).get("plan_id") or plan_id or "").strip() or None
    parent_plan_goal = str((controlling or {}).get("goal") or "").strip() or None
    blockers = extract_blockers(reply_text)
    lead_next = extract_lead_next(reply_text)

    content = build_lead_takeover_message(
        employee_name=employee_name,
        employee_role=role,
        phase=phase,
        goal=goal,
        outcome=outcome,
        reply_text=reply_text,
        run_id=cleaned_run,
        plan_id=resolved_plan_id,
        task_id=task_id,
        parent_plan_goal=parent_plan_goal,
    )
    created_at = _utc_now_iso()
    system_message = chat_store.save_message(
        {
            "message_id": _new_message_id("message_system"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": cleaned_run,
            "role": "system",
            "content": f"Lead takeover after {employee_name or role} ({role}) {phase}.",
            "created_at": created_at,
        }
    )
    agent_message = chat_store.save_message(
        {
            "message_id": _new_message_id("message_agent"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": cleaned_run,
            "role": "agent",
            "content": content,
            "created_at": created_at,
        }
    )
    follow_up = None
    # Full-autonomy loops must keep ownership after both successful and failed
    # specialist shifts. Sticky plan follow-ups keep the original ask as sole truth.
    if create_follow_up_task and phase in {"completed", "failed"}:
        follow_up = enqueue_lead_follow_up_task(
            workspace_id=workspace_id,
            employee_name=employee_name,
            employee_role=role,
            lead_next=lead_next,
            run_id=cleaned_run,
            phase=phase,
            blockers=blockers,
            specialist_goal=goal,
            plan_id=resolved_plan_id,
            task_id=task_id,
        )
    vaxon_flash: dict[str, Any] | None = None
    try:
        from app.workspace_agents.lead_vaxon_handoff import post_ad_hoc_lead_takeover_to_vaxon

        # Publish only Lead-verified fields — never the raw specialist transcript.
        vaxon_flash = post_ad_hoc_lead_takeover_to_vaxon(
            workspace_id=workspace_id,
            run_id=cleaned_run,
            employee_role=role,
            employee_name=employee_name,
            phase=phase if phase in {"completed", "failed"} else phase,
            lead_next=lead_next,
            lead_summary=_lead_summary_from_reply(reply_text),
            lead_thread_id=thread_id,
            lead_message_id=str(agent_message.get("message_id") or "") or None,
            blockers=blockers,
        )
    except Exception as exc:  # noqa: BLE001 — Lead takeover must not fail closed on VAXON flash
        logger.warning("ad-hoc VAXON takeover flash failed: %s", exc)
        vaxon_flash = {"status": "error", "detail": str(exc)}
    spoken: dict[str, Any] | None = None
    try:
        from app.live_events import broadcast_material_change
        from app.workspace_agents.lead_takeover_voice import (
            build_lead_takeover_spoken_line,
            emit_lead_spoken_line,
        )

        broadcast_material_change(receipt_id=f"lead_takeover_{cleaned_run}")
        from app.workspace_agents.lead_fan_out import employee_for_role

        lead_row = employee_for_role(workspace_id, "lead") or {}
        lead_name = str(lead_row.get("name") or "Lead").strip() or "Lead"
        spoken = emit_lead_spoken_line(
            workspace_id=workspace_id,
            line=build_lead_takeover_spoken_line(
                employee_name=employee_name,
                employee_role=role,
                phase=phase,
                reply_text=reply_text,
                lead_name=lead_name,
                parent_plan_goal=parent_plan_goal,
            ),
            receipt_id=f"lead_takeover_voice_{cleaned_run}",
            kind="lead_takeover",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("lead takeover spoken_line failed: %s", exc)
        spoken = {"status": "error", "detail": str(exc)}
    return {
        "status": "posted",
        "thread_id": thread_id,
        "message_id": agent_message.get("message_id"),
        "system_message_id": system_message.get("message_id"),
        "run_id": cleaned_run,
        "lead_next": lead_next,
        "follow_up_task_id": (follow_up or {}).get("task_id"),
        "controlling_plan_id": resolved_plan_id,
        "vaxon_flash": vaxon_flash,
        "spoken": spoken,
    }


__all__ = [
    "build_lead_takeover_message",
    "enqueue_lead_follow_up_task",
    "extract_blockers",
    "extract_lead_next",
    "post_lead_takeover_report",
]
