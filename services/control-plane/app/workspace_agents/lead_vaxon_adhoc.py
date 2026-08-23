"""Persistence for Lead-verified ad-hoc synthesis."""

from __future__ import annotations

from typing import Any

from app.workspace_agents.lead_text import truncate_text as _truncate


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
