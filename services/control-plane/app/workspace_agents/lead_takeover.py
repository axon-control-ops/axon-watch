"""Continuous Lead takeover after specialist shifts (plan-linked or ad-hoc IDE)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.persistence import chat_store, task_store
from app.workspace_agents.lead_checkin_assign import SPECIALIST_ROLES
from app.workspace_agents.lead_fan_out import _employee_id_for_role

logger = logging.getLogger(__name__)

_LEAD_NEXT_RE = re.compile(
    r"(?:blockers?\s*/\s*lead\s*next|lead\s*next|lead:)\s*[-–—:]?\s*(.+)",
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


def _truncate(text: str, *, max_len: int) -> str:
    cleaned = " ".join(str(text or "").strip().split())
    if len(cleaned) <= max_len:
        return cleaned
    return f"{cleaned[: max_len - 1].rstrip()}…"


def _strip_thinking(text: str) -> str:
    raw = str(text or "")
    if ":::thinking" not in raw:
        return raw
    parts = raw.split(":::")
    for part in reversed(parts):
        cleaned = part.strip()
        if cleaned and not cleaned.startswith("thinking") and not cleaned.startswith("tool"):
            return cleaned
    return raw


def extract_lead_next(reply_text: str | None) -> str:
    body = _strip_thinking(reply_text or "")
    if len(body) > 4000:
        body = body[-4000:]
    # Prefer explicit Lead: decision lines from the specialist report.
    for line in body.splitlines():
        cleaned = line.strip().lstrip("-*• ").strip()
        if cleaned.lower().startswith("lead:"):
            return _truncate(cleaned[5:].strip(), max_len=280)
    match = _LEAD_NEXT_RE.search(body)
    if not match:
        return ""
    return _truncate(match.group(1), max_len=280)


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
        if needle in content and "Lead takeover" in content:
            return True
        if str(message.get("run_id") or "").strip() == cleaned_run and "Lead takeover" in content:
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
) -> str:
    name = (employee_name or employee_role or "specialist").strip()
    role = (employee_role or "specialist").strip()
    status = "completed" if phase == "completed" else (phase or "ended")
    excerpt = _truncate(_strip_thinking(reply_text or ""), max_len=420)
    lead_next = extract_lead_next(reply_text)
    lines = [
        f"Lead takeover — {name} ({role}) just {status}.",
        "",
        f"Run: {run_id or '(none)'}",
    ]
    if task_id:
        lines.append(f"Task: {task_id}")
    if plan_id:
        lines.append(f"Plan: {plan_id}")
    goal_line = _truncate(goal, max_len=240)
    if goal_line:
        lines.append(f"Goal: {goal_line}")
    outcome_line = _truncate(outcome, max_len=200)
    if outcome_line:
        lines.append(f"Outcome: {outcome_line}")
    if excerpt:
        lines.extend(["", "Specialist report:", excerpt])
    lines.extend(["", "My read (Lead):"])
    if status == "completed":
        lines.append(
            f"{name} finished their slice. I own the handoff now — "
            "cross-team decisions and next assignments stay with me until you Decide."
        )
    else:
        lines.append(
            f"{name}'s shift {status}. I will triage blockers and reassign if needed."
        )
    if lead_next:
        lines.extend(["", f"Lead next (from specialist): {lead_next}"])
    else:
        lines.extend(
            [
                "",
                "Lead next: review their report, confirm any product Decide gates, "
                "then assign the next specialist or approve ship.",
            ]
        )
    lines.extend(
        [
            "",
            "Open my Lead tab for this rollup. Ask me what to do next.",
            "Confidence: 8/10",
        ]
    )
    return "\n".join(lines)


def enqueue_lead_follow_up_task(
    *,
    workspace_id: str,
    employee_name: str,
    employee_role: str,
    lead_next: str,
    run_id: str,
) -> dict[str, Any] | None:
    """Create an open Lead-owned follow-up so the continuous loop stays explicit."""
    workspace = workspace_id.strip()
    next_line = _truncate(lead_next or "Review specialist completion and decide next handoff.", max_len=220)
    if not workspace:
        return None
    # Dedupe open follow-ups for the same run.
    for status in ("open", "leased"):
        for row in task_store.list_tasks(workspace_id=workspace, status=status, limit=100):
            if str(row.get("owner_role") or "").strip().lower() != "lead":
                continue
            goal = str(row.get("goal") or "")
            if run_id and run_id in goal:
                return row
    name = (employee_name or employee_role or "specialist").strip()
    try:
        return task_store.create_task(
            workspace_id=workspace,
            goal=(
                f"Lead follow-up after {name} ({employee_role}): {next_line} "
                f"[from run {run_id}]"
            ),
            acceptance_criteria=(
                "Post a Lead decision: assign next specialist, approve ship, or ask the operator. "
                "End with Confidence: N/10."
            ),
            risk="normal",
            owner_role="lead",
            attempt_budget=2,
        )
    except task_store.TaskLedgerError as exc:
        logger.warning("lead follow-up task create failed: %s", exc)
        return None


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
        return {"status": "already_posted", "thread_id": thread_id, "run_id": cleaned_run}

    content = build_lead_takeover_message(
        employee_name=employee_name,
        employee_role=role,
        phase=phase,
        goal=goal,
        outcome=outcome,
        reply_text=reply_text,
        run_id=cleaned_run,
        plan_id=plan_id,
        task_id=task_id,
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
    lead_next = extract_lead_next(reply_text)
    if create_follow_up_task and phase == "completed":
        follow_up = enqueue_lead_follow_up_task(
            workspace_id=workspace_id,
            employee_name=employee_name,
            employee_role=role,
            lead_next=lead_next,
            run_id=cleaned_run,
        )
    try:
        from app.live_events import broadcast_material_change

        broadcast_material_change(receipt_id=f"lead_takeover_{cleaned_run}")
    except Exception:  # noqa: BLE001
        pass
    return {
        "status": "posted",
        "thread_id": thread_id,
        "message_id": agent_message.get("message_id"),
        "system_message_id": system_message.get("message_id"),
        "run_id": cleaned_run,
        "lead_next": lead_next,
        "follow_up_task_id": (follow_up or {}).get("task_id"),
    }


__all__ = [
    "build_lead_takeover_message",
    "enqueue_lead_follow_up_task",
    "extract_lead_next",
    "post_lead_takeover_report",
]
