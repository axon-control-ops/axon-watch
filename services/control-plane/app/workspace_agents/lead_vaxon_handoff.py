"""Lead plan → VAXON operator-thread handoff after specialist synthesis."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.persistence import chat_store
from app.workspace_agents import lead_plan_store
from app.workspace_agents.lead_vaxon_adhoc import (
    AD_HOC_TAKEOVER_VAXON_KIND,
    notify_vaxon_after_lead_shift,
    post_ad_hoc_lead_takeover_to_vaxon,
    publish_ad_hoc_synthesis_to_vaxon,
    record_ad_hoc_lead_synthesis,
)
from app.workspace_agents.lead_vaxon_messages import (
    build_ad_hoc_lead_vaxon_message,
    build_lead_synthesis_vaxon_message,
)

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
    # The handoff is VAXON's engagement: it posts the verified rollup and
    # closes the plan instead of leaving an operator-facing engagement chore.
    try:
        lead_plan_store.set_plan_status(plan_id, "completed")
    except ValueError:
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
    plans = lead_plan_store.list_plans_by_status(
        "awaiting_engagement",
        workspace_id=workspace_id,
    )
    pending: list[dict[str, Any]] = []
    for plan in plans:
        plan_id = str(plan.get("plan_id") or "").strip()
        # Repair the legacy state only when the VAXON handoff receipt proves
        # that engagement already happened. Manually reopened plans remain
        # visible to their owner until they are acted on.
        if plan_id and _handoff_already_posted(plan_id):
            try:
                lead_plan_store.set_plan_status(plan_id, "completed")
            except ValueError:
                pass
            continue
        pending.append(plan)
    return pending


def count_awaiting_engagement_plans(*, workspace_id: str | None = None) -> int:
    """Return genuinely unresolved legacy plans after settling VAXON handoffs."""
    return len(list_awaiting_engagement_plans(workspace_id=workspace_id))


__all__ = [
    "AD_HOC_TAKEOVER_VAXON_KIND",
    "HANDOFF_RECEIPT_KIND",
    "build_ad_hoc_lead_vaxon_message",
    "build_lead_synthesis_vaxon_message",
    "count_awaiting_engagement_plans",
    "list_awaiting_engagement_plans",
    "notify_vaxon_after_lead_shift",
    "post_ad_hoc_lead_takeover_to_vaxon",
    "post_lead_synthesis_to_vaxon",
    "publish_ad_hoc_synthesis_to_vaxon",
    "record_ad_hoc_lead_synthesis",
]
