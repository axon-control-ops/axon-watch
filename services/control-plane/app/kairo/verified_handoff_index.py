"""Index verified Lead → VAXON handoffs for deterministic REPORT.

Receipt-first: plan synthesis receipts and ad-hoc Lead synthesis/VAXON receipts.
Never scrape specialist IDE transcripts into the operator stand-up.
"""

from __future__ import annotations

from typing import Any

from app.workspace_agents.lead_vaxon_handoff import HANDOFF_RECEIPT_KIND


def _truncate(text: str, *, max_len: int) -> str:
    cleaned = " ".join(str(text or "").strip().split())
    if len(cleaned) <= max_len:
        return cleaned
    return f"{cleaned[: max_len - 1].rstrip()}…"


def _plan_handoff_rows(*, workspace_id: str | None, limit: int) -> list[dict[str, Any]]:
    from app.workspace_agents import lead_plan_store

    rows = lead_plan_store.list_receipts_by_kind(
        HANDOFF_RECEIPT_KIND,
        workspace_id=workspace_id,
        limit=limit,
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        summary = _truncate(str(payload.get("summary") or ""), max_len=280)
        plan_id = str(row.get("plan_id") or "").strip()
        out.append(
            {
                "kind": "plan_synthesis",
                "receipt_id": row.get("receipt_id"),
                "workspace_id": row.get("workspace_id"),
                "plan_id": plan_id,
                "run_id": None,
                "created_at": row.get("created_at"),
                "employee_name": None,
                "employee_role": "lead",
                "phase": "awaiting_engagement",
                "lead_summary": summary,
                "lead_next": "",
                "headline": (
                    f"Lead-team plan {plan_id} rollup ready"
                    + (f" — {summary}" if summary else "")
                ).strip(" —"),
                "message_id": payload.get("message_id"),
                "thread_id": payload.get("thread_id"),
            }
        )
    return out


def _ad_hoc_handoff_rows(*, workspace_id: str | None, limit: int) -> list[dict[str, Any]]:
    from app.workspace_agents import lead_adhoc_receipt_store

    rows = lead_adhoc_receipt_store.list_verified_vaxon_handoffs(
        workspace_id=workspace_id,
        limit=limit,
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        name = str(payload.get("employee_name") or "").strip() or "specialist"
        role = str(payload.get("employee_role") or "").strip() or "specialist"
        phase = str(payload.get("phase") or "ended").strip()
        summary = _truncate(str(payload.get("lead_summary") or ""), max_len=280)
        lead_next = _truncate(str(payload.get("lead_next") or ""), max_len=220)
        headline_bits = [f"{name} ({role}) {phase}"]
        if summary:
            headline_bits.append(summary)
        out.append(
            {
                "kind": "ad_hoc_takeover",
                "receipt_id": row.get("receipt_id"),
                "workspace_id": row.get("workspace_id"),
                "plan_id": None,
                "run_id": row.get("run_id"),
                "created_at": row.get("created_at"),
                "employee_name": name,
                "employee_role": role,
                "phase": phase,
                "lead_summary": summary,
                "lead_next": lead_next,
                "headline": " — ".join(headline_bits),
                "message_id": payload.get("message_id"),
                "thread_id": payload.get("thread_id"),
            }
        )
    return out


def list_verified_lead_handoffs(
    *,
    workspace_id: str | None = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Return Lead-verified VAXON handoffs newest-first, deduped by receipt_id."""
    max_limit = max(1, min(40, int(limit or 12)))
    combined = _plan_handoff_rows(workspace_id=workspace_id, limit=max_limit)
    combined.extend(_ad_hoc_handoff_rows(workspace_id=workspace_id, limit=max_limit))
    combined.sort(
        key=lambda row: (
            str(row.get("created_at") or ""),
            str(row.get("receipt_id") or ""),
        ),
        reverse=True,
    )
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in combined:
        key = str(row.get("receipt_id") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row)
        if len(out) >= max_limit:
            break
    return out


__all__ = ["list_verified_lead_handoffs"]
