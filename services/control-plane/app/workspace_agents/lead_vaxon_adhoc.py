"""Ad-hoc Lead synthesis → VAXON operator-thread handoffs."""

from __future__ import annotations

from typing import Any

from app.persistence import chat_store
from app.workspace_agents import lead_adhoc_receipt_store
from app.workspace_agents.lead_text import truncate_text as _truncate
from app.workspace_agents.lead_vaxon_common import (
    broadcast_material_change_safe,
    get_or_create_operator_thread,
    new_message_id,
    utc_now_iso,
)
from app.workspace_agents.lead_vaxon_messages import build_ad_hoc_lead_vaxon_message

AD_HOC_TAKEOVER_VAXON_KIND = "lead_takeover_vaxon_posted"


def record_ad_hoc_lead_synthesis(
    *,
    workspace_id: str,
    run_id: str,
    employee_role: str,
    employee_name: str,
    phase: str,
    lead_next: str = "",
    lead_summary: str = "",
    lead_thread_id: str | None = None,
    lead_message_id: str | None = None,
    blockers: str = "",
) -> dict[str, Any]:
    """Persist Lead-verified synthesis fields for an ad-hoc specialist completion."""
    cleaned_run = str(run_id or "").strip()
    workspace = str(workspace_id or "").strip()
    if not cleaned_run or not workspace:
        return {"status": "skipped_missing_ids"}

    prior = lead_adhoc_receipt_store.find_receipt_for_run(
        run_id=cleaned_run,
        kind=lead_adhoc_receipt_store.KIND_LEAD_SYNTHESIS,
    )
    if prior is not None:
        return {
            "status": "already_recorded",
            "receipt_id": prior.get("receipt_id"),
            "payload": prior.get("payload") or {},
            "run_id": cleaned_run,
        }

    payload = {
        "employee_name": (employee_name or employee_role or "specialist").strip(),
        "employee_role": (employee_role or "specialist").strip(),
        "phase": phase if phase in {"completed", "failed"} else (phase or "ended"),
        "lead_next": _truncate(lead_next, max_len=280),
        "lead_summary": _truncate(lead_summary, max_len=420),
        "blockers": _truncate(blockers, max_len=280),
        "lead_thread_id": lead_thread_id,
        "lead_message_id": lead_message_id,
    }
    receipt = lead_adhoc_receipt_store.append_receipt(
        workspace_id=workspace,
        run_id=cleaned_run,
        kind=lead_adhoc_receipt_store.KIND_LEAD_SYNTHESIS,
        payload=payload,
    )
    return {
        "status": "recorded",
        "receipt_id": receipt["receipt_id"],
        "payload": payload,
        "run_id": cleaned_run,
    }


def publish_ad_hoc_synthesis_to_vaxon(
    *,
    workspace_id: str,
    run_id: str,
    synthesis_receipt_id: str | None = None,
) -> dict[str, Any]:
    """Publish VAXON flash only from a Lead synthesis receipt (never raw specialist text)."""
    cleaned_run = str(run_id or "").strip()
    workspace = str(workspace_id or "").strip()
    if not cleaned_run or not workspace:
        return {"status": "skipped_missing_ids"}

    prior_vaxon = lead_adhoc_receipt_store.find_receipt_for_run(
        run_id=cleaned_run,
        kind=lead_adhoc_receipt_store.KIND_VAXON_POSTED,
    )
    if prior_vaxon is not None:
        payload = prior_vaxon.get("payload") or {}
        return {
            "status": "already_posted",
            "receipt_id": prior_vaxon.get("receipt_id"),
            "thread_id": payload.get("thread_id"),
            "message_id": payload.get("message_id"),
            "run_id": cleaned_run,
            "kind": AD_HOC_TAKEOVER_VAXON_KIND,
        }

    synthesis = lead_adhoc_receipt_store.find_receipt_for_run(
        run_id=cleaned_run,
        kind=lead_adhoc_receipt_store.KIND_LEAD_SYNTHESIS,
    )
    if synthesis is None:
        return {"status": "skipped_missing_synthesis", "run_id": cleaned_run}

    fields = synthesis.get("payload") or {}
    created_at = utc_now_iso()
    thread = get_or_create_operator_thread(workspace, created_at=created_at)
    thread_id = str(thread["thread_id"])
    content = build_ad_hoc_lead_vaxon_message(
        workspace_id=workspace,
        employee_name=str(fields.get("employee_name") or ""),
        employee_role=str(fields.get("employee_role") or ""),
        phase=str(fields.get("phase") or "ended"),
        run_id=cleaned_run,
        lead_next=str(fields.get("lead_next") or ""),
        lead_summary=str(fields.get("lead_summary") or ""),
    )
    system_message = chat_store.save_message(
        {
            "message_id": new_message_id("message_system"),
            "thread_id": thread_id,
            "workspace_id": workspace,
            "run_id": cleaned_run,
            "role": "system",
            "content": (
                f"Lead synthesis for {fields.get('employee_name') or fields.get('employee_role')} "
                f"({fields.get('employee_role')}) {fields.get('phase')} — VAXON fleet flash."
            ),
            "created_at": created_at,
        }
    )
    agent_message = chat_store.save_message(
        {
            "message_id": new_message_id("message_agent"),
            "thread_id": thread_id,
            "workspace_id": workspace,
            "run_id": cleaned_run,
            "role": "agent",
            "content": content,
            "created_at": created_at,
        }
    )
    receipt = lead_adhoc_receipt_store.append_receipt(
        workspace_id=workspace,
        run_id=cleaned_run,
        kind=lead_adhoc_receipt_store.KIND_VAXON_POSTED,
        payload={
            "thread_id": thread_id,
            "message_id": agent_message["message_id"],
            "system_message_id": system_message["message_id"],
            "synthesis_receipt_id": synthesis_receipt_id or synthesis.get("receipt_id"),
            "employee_name": fields.get("employee_name"),
            "employee_role": fields.get("employee_role"),
            "phase": fields.get("phase"),
            "lead_next": fields.get("lead_next"),
            "lead_summary": fields.get("lead_summary"),
            "content": content,
        },
    )
    broadcast_material_change_safe(receipt_id=f"lead_takeover_vaxon_{cleaned_run}")
    return {
        "status": "posted",
        "thread_id": thread_id,
        "message_id": agent_message["message_id"],
        "system_message_id": system_message["message_id"],
        "run_id": cleaned_run,
        "kind": AD_HOC_TAKEOVER_VAXON_KIND,
        "receipt_id": receipt["receipt_id"],
        "synthesis_receipt_id": synthesis.get("receipt_id"),
        "content": content,
    }


def post_ad_hoc_lead_takeover_to_vaxon(
    *,
    workspace_id: str,
    run_id: str,
    employee_role: str,
    employee_name: str,
    phase: str,
    lead_next: str = "",
    lead_summary: str = "",
    lead_thread_id: str | None = None,
    lead_message_id: str | None = None,
    blockers: str = "",
    reply_text: str | None = None,
) -> dict[str, Any]:
    """Record Lead synthesis then publish one VAXON flash from that receipt.

    ``reply_text`` is accepted for backwards-compatible callers but is never posted
    to VAXON — only Lead-verified ``lead_summary`` / ``lead_next`` fields are used.
    """
    del reply_text  # never publish raw specialist transcripts to VAXON
    synthesis = record_ad_hoc_lead_synthesis(
        workspace_id=workspace_id,
        run_id=run_id,
        employee_role=employee_role,
        employee_name=employee_name,
        phase=phase,
        lead_next=lead_next,
        lead_summary=lead_summary,
        lead_thread_id=lead_thread_id,
        lead_message_id=lead_message_id,
        blockers=blockers,
    )
    if synthesis.get("status") not in {"recorded", "already_recorded"}:
        return synthesis
    published = publish_ad_hoc_synthesis_to_vaxon(
        workspace_id=workspace_id,
        run_id=run_id,
        synthesis_receipt_id=str(synthesis.get("receipt_id") or "") or None,
    )
    published["synthesis"] = synthesis
    return published


__all__ = [
    "AD_HOC_TAKEOVER_VAXON_KIND",
    "post_ad_hoc_lead_takeover_to_vaxon",
    "publish_ad_hoc_synthesis_to_vaxon",
    "record_ad_hoc_lead_synthesis",
]
