"""Lead plan → VAXON operator-thread handoff after specialist synthesis."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.persistence import chat_store
from app.workspace_agents import lead_plan_store
from app.workspace_agents.lead_text import truncate_text as _truncate
from app.workspace_agents.lead_vaxon_messages import (
    build_ad_hoc_lead_vaxon_message,
    build_lead_synthesis_vaxon_message,
)

HANDOFF_RECEIPT_KIND = "lead_synthesis_vaxon_posted"
AD_HOC_TAKEOVER_VAXON_KIND = "lead_takeover_vaxon_posted"


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
    from app.workspace_agents import lead_adhoc_receipt_store

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
    from app.workspace_agents import lead_adhoc_receipt_store

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
    created_at = _utc_now_iso()
    thread = chat_store.get_latest_thread_for_workspace(
        workspace,
        thread_kind="operator",
    )
    if thread is None:
        thread = chat_store.create_thread(
            workspace_id=workspace,
            run_id=None,
            created_at=created_at,
            thread_kind="operator",
            title="VAXON",
        )
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
            "message_id": _new_message_id("message_system"),
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
            "message_id": _new_message_id("message_agent"),
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
    try:
        from app.live_events import broadcast_material_change

        broadcast_material_change(receipt_id=f"lead_takeover_vaxon_{cleaned_run}")
    except Exception:
        pass
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
