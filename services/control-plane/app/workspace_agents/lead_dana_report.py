"""Lead plan → Dana IDE reports (specialist status + human rollup for the operator)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.persistence import chat_store
from app.workspace_agents import lead_plan_store
from app.workspace_agents.lead_fan_out import _employee_id_for_role

DANA_SYNTHESIS_RECEIPT_KIND = "lead_synthesis_dana_posted"
SPECIALIST_STATUS_RECEIPT_KIND = "lead_specialist_status_posted"


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


def _receipt_already_posted(plan_id: str, kind: str, *, run_id: str | None = None) -> bool:
    for row in lead_plan_store.list_receipts(plan_id):
        if str(row.get("kind") or "") != kind:
            continue
        if run_id is None:
            return True
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        if str(payload.get("run_id") or "").strip() == run_id:
            return True
    return False


def _ensure_dana_ide_thread(workspace_id: str) -> dict[str, Any] | None:
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
            title="Dana · Lead",
            employee_id=employee_id,
            employee_role="lead",
        )
    return thread


def build_lead_synthesis_dana_message(
    *,
    plan_id: str,
    goal: str,
    summary: str,
    findings: list[dict[str, Any]],
) -> str:
    """Detailed Lead voice rollup for the operator (Dana IDE thread)."""
    goal_line = _truncate(goal, max_len=280) or "Lead plan"
    completed = sum(
        1 for row in findings if str(row.get("status") or "").lower() == "completed"
    )
    failed = sum(1 for row in findings if str(row.get("status") or "").lower() == "failed")
    cancelled = sum(
        1 for row in findings if str(row.get("status") or "").lower() == "cancelled"
    )
    lines = [
        "Dana here — Lead team rollup for you.",
        "",
        f"Goal: {goal_line}",
        f"Plan: {plan_id}",
        f"Overall: {completed} completed · {failed} failed · {cancelled} cancelled "
        f"(of {len(findings)} specialists).",
        "",
        "Specialist results:",
    ]
    for index, row in enumerate(findings[:8], start=1):
        owner = str(row.get("assignee_name") or row.get("owner_role") or "specialist").strip()
        role = str(row.get("owner_role") or "").strip()
        status = str(row.get("status") or "unknown").strip()
        outcome = _truncate(str(row.get("outcome") or ""), max_len=180)
        task_goal = _truncate(str(row.get("goal") or ""), max_len=180)
        excerpt = _truncate(str(row.get("specialist_reply_excerpt") or ""), max_len=320)
        run_ids = [str(item).strip() for item in (row.get("run_ids") or []) if str(item).strip()]
        run_bit = ", ".join(run_ids[:3]) if run_ids else "(no run id)"
        lines.append(f"{index}. {owner} ({role}) — {status}")
        if task_goal:
            lines.append(f"   Task: {task_goal}")
        if outcome:
            lines.append(f"   Outcome: {outcome}")
        lines.append(f"   Runs: {run_bit}")
        if excerpt:
            lines.append(f"   Report: {excerpt}")
        lines.append("")

    clean_summary = _truncate(summary, max_len=400)
    if clean_summary:
        lines.append(f"Compressed outcome line: {clean_summary}")
        lines.append("")

    lines.extend(
        [
            "Next best steps (operator):",
            "1) Tell me which specialist to dig into, or what to approve next.",
            "2) Confirm any blocked live checks (auth/network/headcount) before rollout.",
            "3) I will keep holding cross-team decisions until you engage.",
            "",
            "Ask me anything about this rollup — I stay with you conversationally.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def post_lead_synthesis_to_dana_ide(
    *,
    plan_id: str,
    workspace_id: str,
    goal: str,
    summary: str,
    findings: list[dict[str, Any]],
    synthesis_receipt_id: str | None = None,
) -> dict[str, Any]:
    """Post Dana's detailed human rollup into the Lead IDE thread."""
    if _receipt_already_posted(plan_id, DANA_SYNTHESIS_RECEIPT_KIND):
        prior = next(
            (
                row
                for row in lead_plan_store.list_receipts(plan_id)
                if str(row.get("kind") or "") == DANA_SYNTHESIS_RECEIPT_KIND
            ),
            None,
        )
        payload = (prior or {}).get("payload") if isinstance(prior, dict) else {}
        return {
            "plan_id": plan_id,
            "status": "already_posted",
            "receipt_id": (prior or {}).get("receipt_id"),
            "message_id": (payload or {}).get("message_id"),
            "thread_id": (payload or {}).get("thread_id"),
        }

    thread = _ensure_dana_ide_thread(workspace_id)
    if thread is None:
        return {
            "plan_id": plan_id,
            "status": "skipped_no_lead",
            "detail": "no lead employee_id in roster",
        }

    created_at = _utc_now_iso()
    thread_id = str(thread["thread_id"])
    content = build_lead_synthesis_dana_message(
        plan_id=plan_id,
        goal=goal,
        summary=summary,
        findings=findings,
    )
    system_message = chat_store.save_message(
        {
            "message_id": _new_message_id("message_system"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": None,
            "role": "system",
            "content": f"Lead plan {plan_id} synthesized — Dana rollup for the operator.",
            "created_at": created_at,
        }
    )
    agent_message = chat_store.save_message(
        {
            "message_id": _new_message_id("message_agent"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": None,
            "role": "agent",
            "content": content,
            "created_at": created_at,
        }
    )
    receipt = lead_plan_store.append_receipt(
        plan_id=plan_id,
        workspace_id=workspace_id,
        kind=DANA_SYNTHESIS_RECEIPT_KIND,
        payload={
            "thread_id": thread_id,
            "message_id": agent_message["message_id"],
            "system_message_id": system_message["message_id"],
            "synthesis_receipt_id": synthesis_receipt_id,
            "summary": summary,
        },
    )
    try:
        from app.live_events import broadcast_material_change

        broadcast_material_change(receipt_id=str(receipt.get("receipt_id") or plan_id))
    except Exception:
        pass

    return {
        "plan_id": plan_id,
        "status": "posted",
        "receipt_id": receipt["receipt_id"],
        "message_id": agent_message["message_id"],
        "thread_id": thread_id,
        "content": content,
    }


def post_specialist_status_to_dana(
    *,
    workspace_id: str,
    plan_id: str,
    task_id: str,
    plan_key: str | None,
    run_id: str,
    employee_role: str,
    employee_name: str,
    phase: str,
    goal: str | None = None,
    outcome: str | None = None,
    reply_excerpt: str | None = None,
) -> dict[str, Any]:
    """Specialists always report completion/failure into Dana's IDE thread."""
    cleaned_run = str(run_id or "").strip()
    if not cleaned_run or _receipt_already_posted(
        plan_id, SPECIALIST_STATUS_RECEIPT_KIND, run_id=cleaned_run
    ):
        return {"plan_id": plan_id, "status": "already_posted", "run_id": cleaned_run}

    thread = _ensure_dana_ide_thread(workspace_id)
    if thread is None:
        return {"plan_id": plan_id, "status": "skipped_no_lead", "run_id": cleaned_run}

    created_at = _utc_now_iso()
    thread_id = str(thread["thread_id"])
    name = (employee_name or employee_role or "specialist").strip()
    role = (employee_role or "specialist").strip()
    status_word = "completed" if phase == "completed" else phase
    lines = [
        f"{name} ({role}) reported in — shift {status_word}.",
        f"Task: {plan_key or task_id}",
        f"Run: {cleaned_run}",
    ]
    goal_line = _truncate(goal or "", max_len=220)
    if goal_line:
        lines.append(f"Goal: {goal_line}")
    outcome_line = _truncate(outcome or "", max_len=180)
    if outcome_line:
        lines.append(f"Outcome: {outcome_line}")
    excerpt = _truncate(reply_excerpt or "", max_len=280)
    if excerpt:
        lines.append(f"Excerpt: {excerpt}")
    lines.append("I will synthesize a full operator rollup when every specialist is terminal.")

    agent_message = chat_store.save_message(
        {
            "message_id": _new_message_id("message_agent"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": cleaned_run,
            "role": "agent",
            "content": "\n".join(lines),
            "created_at": created_at,
        }
    )
    receipt = lead_plan_store.append_receipt(
        plan_id=plan_id,
        workspace_id=workspace_id,
        kind=SPECIALIST_STATUS_RECEIPT_KIND,
        payload={
            "thread_id": thread_id,
            "message_id": agent_message["message_id"],
            "task_id": task_id,
            "plan_key": plan_key,
            "run_id": cleaned_run,
            "employee_role": role,
            "phase": phase,
        },
    )
    try:
        from app.live_events import broadcast_material_change

        broadcast_material_change(receipt_id=str(receipt.get("receipt_id") or cleaned_run))
    except Exception:
        pass

    return {
        "plan_id": plan_id,
        "status": "posted",
        "receipt_id": receipt["receipt_id"],
        "message_id": agent_message["message_id"],
        "thread_id": thread_id,
        "run_id": cleaned_run,
    }


__all__ = [
    "DANA_SYNTHESIS_RECEIPT_KIND",
    "SPECIALIST_STATUS_RECEIPT_KIND",
    "build_lead_synthesis_dana_message",
    "post_lead_synthesis_to_dana_ide",
    "post_specialist_status_to_dana",
]
