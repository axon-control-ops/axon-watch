"""Lead plan → VAXON operator-thread handoff after specialist synthesis."""

from __future__ import annotations

from typing import Any

from app.persistence import chat_store
from app.workspace_agents import lead_plan_store
from app.workspace_agents.lead_vaxon_adhoc import (
    AD_HOC_TAKEOVER_VAXON_KIND,
    post_ad_hoc_lead_takeover_to_vaxon,
    publish_ad_hoc_synthesis_to_vaxon,
    record_ad_hoc_lead_synthesis,
)
from app.workspace_agents.lead_vaxon_common import (
    broadcast_material_change_safe,
    get_or_create_operator_thread,
    new_message_id,
    utc_now_iso,
)
from app.workspace_agents.lead_vaxon_messages import (
    build_ad_hoc_lead_vaxon_message,
    build_lead_synthesis_vaxon_message,
)

HANDOFF_RECEIPT_KIND = "lead_synthesis_vaxon_posted"


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

    created_at = utc_now_iso()
    thread = get_or_create_operator_thread(workspace_id, created_at=created_at)
    thread_id = str(thread["thread_id"])
    content = build_lead_synthesis_vaxon_message(
        plan_id=plan_id,
        goal=goal,
        summary=summary,
        findings=findings,
    )
    system_message = chat_store.save_message(
        {
            "message_id": new_message_id("message_system"),
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
            "message_id": new_message_id("message_agent"),
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

    broadcast_material_change_safe(receipt_id=str(receipt.get("receipt_id") or plan_id))

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


def notify_vaxon_after_lead_shift(
    *,
    workspace_id: str,
    run_id: str,
    employee_name: str,
    phase: str,
    reply_text: str | None = None,
) -> dict[str, Any]:
    """When Dana/Lead finishes their own shift, publish one VAXON operator flash.

    Specialists already reach VAXON via Lead takeover. Lead self-completions were
    previously silent — REPORT and the operator thread never saw the rollup.
    """
    cleaned_run = str(run_id or "").strip()
    workspace = str(workspace_id or "").strip()
    if not cleaned_run or not workspace:
        return {"status": "skipped_missing_ids"}

    from app.workspace_agents.lead_takeover import extract_blockers, extract_lead_next
    from app.workspace_agents.lead_text import lead_summary_from_reply
    from app.workspace_agents.lead_takeover_voice import emit_lead_shift_spoken

    name = (employee_name or "Lead").strip() or "Lead"
    terminal = phase if phase in {"completed", "failed"} else (phase or "ended")
    try:
        vaxon_flash = post_ad_hoc_lead_takeover_to_vaxon(
            workspace_id=workspace,
            run_id=cleaned_run,
            employee_role="lead",
            employee_name=name,
            phase=terminal,
            lead_next=extract_lead_next(reply_text),
            lead_summary=lead_summary_from_reply(reply_text),
            blockers=extract_blockers(reply_text),
            reply_text=None,
        )
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "detail": str(exc), "run_id": cleaned_run}

    try:
        spoken = emit_lead_shift_spoken(
            workspace_id=workspace,
            run_id=cleaned_run,
            employee_name=name,
            phase=terminal,
            reply_text=reply_text,
        )
    except Exception as exc:  # noqa: BLE001
        spoken = {"status": "error", "detail": str(exc)}

    return {
        "status": "ok_lead_shift",
        "run_id": cleaned_run,
        "vaxon_flash": vaxon_flash,
        "spoken": spoken,
    }


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
