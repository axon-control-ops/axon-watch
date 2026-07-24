"""Lead plan → VAXON operator-thread handoff after specialist synthesis."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.persistence import chat_store
from app.workspace_agents import lead_plan_store

HANDOFF_RECEIPT_KIND = "lead_synthesis_vaxon_posted"


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


def build_lead_synthesis_vaxon_message(
    *,
    plan_id: str,
    goal: str,
    summary: str,
    findings: list[dict[str, Any]],
) -> str:
    """Build one operator-facing VAXON rollup (no PII invention)."""
    goal_line = _truncate(goal, max_len=280) or "Lead plan"
    lines = [
        "VAXON: Lead team rollup is ready for your review.",
        f"Goal: {goal_line}",
        f"Plan: {plan_id}",
    ]
    clean_summary = _truncate(summary, max_len=500)
    if clean_summary:
        lines.append(f"Outcome: {clean_summary}")

    for row in findings[:8]:
        owner = str(row.get("assignee_name") or row.get("owner_role") or "specialist").strip()
        status = str(row.get("status") or "").strip() or "unknown"
        outcome = _truncate(str(row.get("outcome") or ""), max_len=160)
        excerpt = _truncate(str(row.get("specialist_reply_excerpt") or ""), max_len=160)
        run_ids = [str(item).strip() for item in (row.get("run_ids") or []) if str(item).strip()]
        run_bit = f" · runs {', '.join(run_ids[:3])}" if run_ids else ""
        detail = f"{owner}: {status}"
        if outcome:
            detail = f"{detail} ({outcome})"
        if excerpt:
            detail = f"{detail} — {excerpt}"
        lines.append(f"- {detail}{run_bit}")

    lines.append("Open Dana's Lead thread for the full narrative, or ask me what to do next.")
    return "\n".join(lines)


def _handoff_already_posted(plan_id: str) -> bool:
    return any(
        str(row.get("kind") or "") == HANDOFF_RECEIPT_KIND
        for row in lead_plan_store.list_receipts(plan_id)
    )


def post_lead_synthesis_to_vaxon(
    *,
    plan_id: str,
    workspace_id: str,
    goal: str,
    summary: str,
    findings: list[dict[str, Any]],
    synthesis_receipt_id: str | None = None,
) -> dict[str, Any]:
    """Post one VAXON agent message into the workspace operator thread.

    Idempotent: a second call after a successful handoff returns the prior receipt.
    Broadcasts material_change so the console refreshes quietly (no spoken interrupt).
    """
    if _handoff_already_posted(plan_id):
        prior = next(
            (
                row
                for row in lead_plan_store.list_receipts(plan_id)
                if str(row.get("kind") or "") == HANDOFF_RECEIPT_KIND
            ),
            None,
        )
        return {
            "plan_id": plan_id,
            "status": "already_posted",
            "receipt_id": (prior or {}).get("receipt_id"),
            "message_id": ((prior or {}).get("payload") or {}).get("message_id"),
            "thread_id": ((prior or {}).get("payload") or {}).get("thread_id"),
        }

    created_at = _utc_now_iso()
    thread = chat_store.get_latest_thread_for_workspace(
        workspace_id,
        thread_kind="operator",
    )
    if thread is None:
        thread = chat_store.create_thread(
            workspace_id=workspace_id,
            run_id=None,
            created_at=created_at,
            thread_kind="operator",
            title="VAXON",
        )
    thread_id = str(thread["thread_id"])
    content = build_lead_synthesis_vaxon_message(
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
            "run_id": thread.get("run_id"),
            "role": "system",
            "content": (
                f"Lead plan {plan_id} synthesized — VAXON engagement handoff."
            ),
            "created_at": created_at,
        }
    )
    agent_message = chat_store.save_message(
        {
            "message_id": _new_message_id("message_agent"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": thread.get("run_id"),
            "role": "agent",
            "content": content,
            "created_at": created_at,
        }
    )
    receipt = lead_plan_store.append_receipt(
        plan_id=plan_id,
        workspace_id=workspace_id,
        kind=HANDOFF_RECEIPT_KIND,
        payload={
            "thread_id": thread_id,
            "message_id": agent_message["message_id"],
            "system_message_id": system_message["message_id"],
            "synthesis_receipt_id": synthesis_receipt_id,
            "summary": summary,
        },
    )
    try:
        lead_plan_store.set_plan_status(plan_id, "awaiting_engagement")
    except ValueError:
        # Older DBs or unexpected status — synthesis already marked completed.
        pass

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


def list_awaiting_engagement_plans(*, workspace_id: str | None = None) -> list[dict[str, Any]]:
    return lead_plan_store.list_plans_by_status(
        "awaiting_engagement",
        workspace_id=workspace_id,
    )


def count_awaiting_engagement_plans(*, workspace_id: str | None = None) -> int:
    """Count Lead plans waiting for operator engagement via VAXON."""
    return len(list_awaiting_engagement_plans(workspace_id=workspace_id))


__all__ = [
    "HANDOFF_RECEIPT_KIND",
    "build_lead_synthesis_vaxon_message",
    "count_awaiting_engagement_plans",
    "list_awaiting_engagement_plans",
    "post_lead_synthesis_to_vaxon",
]
