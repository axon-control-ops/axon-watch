"""Posting a Lead team check-in report into the Lead's own IDE thread.

Extracted out of lead_team_checkin.py (status-rendering slice) to keep that
file under its file-size ratchet budget — see hotspot_budgets.json's note on
that entry.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.persistence import chat_store
from app.workspace_agents.lead_checkin_assign import LeadCheckinFinding
from app.workspace_agents.lead_checkin_report import format_lead_checkin_message


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _employee_id_for_role(workspace_id: str, role: str) -> str | None:
    from app.workspace_agents import build_company_roster

    company = build_company_roster(workspace_id)
    rows = company.get("employees") if isinstance(company, dict) else None
    if not isinstance(rows, list):
        return None
    want = role.strip().lower()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("role") or "").strip().lower() == want:
            employee_id = str(row.get("employee_id") or "").strip()
            return employee_id or None
    return None


def post_lead_checkin_message(
    *,
    workspace_id: str,
    findings: list[LeadCheckinFinding],
    assigned: list[dict[str, Any]],
) -> str | None:
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
            title="Lead · team check-in",
            employee_id=employee_id,
            employee_role="lead",
        )
    thread_id = str(thread["thread_id"])
    message_id = f"message_system_{uuid4().hex}"
    chat_store.save_message(
        {
            "message_id": message_id,
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": None,
            "role": "agent",
            "content": format_lead_checkin_message(findings, assigned),
            "created_at": created_at,
        }
    )
    return message_id


__all__ = ["post_lead_checkin_message"]
