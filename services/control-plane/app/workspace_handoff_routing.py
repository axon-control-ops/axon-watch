"""Automatic cross-workspace ticket routing + team communication."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.persistence import chat_store, handoff_store, task_store
from app.workspace_agents import build_company_roster
from app.workspace_agents.teammate_route import route_teammate_decision
from app.workspace_catalog import get_workspace_record

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _truncate(text: str, *, max_len: int) -> str:
    cleaned = " ".join(str(text or "").strip().split())
    if len(cleaned) <= max_len:
        return cleaned
    return f"{cleaned[: max_len - 1].rstrip()}…"


def _workspace_label(workspace_id: str) -> str:
    try:
        record = get_workspace_record(workspace_id)
    except Exception:  # noqa: BLE001 — label is best-effort
        record = {}
    named = str(record.get("display_name") or "").strip()
    if named:
        return named
    suffix = workspace_id.removeprefix("workspace_").replace("-", " ").replace("_", " ").strip()
    if not suffix:
        return workspace_id
    return " ".join(part.capitalize() for part in suffix.split())


def _lead_employee(workspace_id: str) -> dict[str, str] | None:
    try:
        company = build_company_roster(workspace_id)
    except Exception:  # noqa: BLE001 — routing falls back without Lead
        return None
    for row in company.get("employees") or []:
        if not isinstance(row, dict):
            continue
        role = str(row.get("role") or "").strip().lower()
        if role != "lead":
            continue
        employee_id = str(row.get("employee_id") or "").strip()
        if not employee_id:
            continue
        return {
            "employee_id": employee_id,
            "name": str(row.get("name") or "Lead").strip() or "Lead",
            "role": "lead",
        }
    return None


def _post_target_thread_messages(
    *,
    workspace_id: str,
    handoff_id: str,
    task_id: str,
    task_text: str,
    reason: str,
    source_workspace_id: str,
    employee_id: str,
    employee_role: str,
    employee_name: str,
) -> str | None:
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
            title=f"{employee_name} · cross-workspace handoff",
            employee_id=employee_id,
            employee_role=employee_role,
        )
    thread_id = str(thread["thread_id"])
    source_label = _workspace_label(source_workspace_id)
    goal_line = _truncate(task_text, max_len=280)
    reason_line = _truncate(reason, max_len=180)
    chat_store.save_message(
        {
            "message_id": f"message_system_{uuid4().hex}",
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": None,
            "role": "system",
            "content": (
                f"Cross-workspace ticket routed from {source_label}. "
                f"Handoff {handoff_id} → task {task_id}."
            ),
            "created_at": created_at,
        }
    )
    agent_lines = [
        f"Incoming handoff from {source_label}.",
        f"Ticket: {goal_line or '(no goal text)'}",
    ]
    if reason_line:
        agent_lines.append(f"Reason: {reason_line}")
    agent_lines.append(
        "This task is on the target workspace board. "
        "Pick it up here or ask Lead to fan it out."
    )
    chat_store.save_message(
        {
            "message_id": f"message_agent_{uuid4().hex}",
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": None,
            "role": "agent",
            "content": "\n".join(agent_lines),
            "created_at": created_at,
        }
    )
    return thread_id


def _post_source_ack(
    *,
    workspace_id: str,
    handoff_id: str,
    target_workspace_id: str,
    task_id: str,
    routed_name: str,
    task_text: str,
) -> str | None:
    lead = _lead_employee(workspace_id)
    if lead is None:
        return None
    created_at = _utc_now_iso()
    thread = chat_store.find_thread_for_employee(
        workspace_id,
        employee_id=lead["employee_id"],
        thread_kind="ide",
    )
    if thread is None:
        thread = chat_store.create_thread(
            workspace_id=workspace_id,
            run_id=None,
            created_at=created_at,
            thread_kind="ide",
            title=f"{lead['name']} · handoff sent",
            employee_id=lead["employee_id"],
            employee_role="lead",
        )
    thread_id = str(thread["thread_id"])
    target_label = _workspace_label(target_workspace_id)
    chat_store.save_message(
        {
            "message_id": f"message_system_{uuid4().hex}",
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": None,
            "role": "system",
            "content": (
                f"Handoff {handoff_id} routed to {target_label} as task {task_id} "
                f"(owner {routed_name})."
            ),
            "created_at": created_at,
        }
    )
    chat_store.save_message(
        {
            "message_id": f"message_agent_{uuid4().hex}",
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": None,
            "role": "agent",
            "content": (
                f"I handed “{_truncate(task_text, max_len=160)}” to {target_label}. "
                f"{routed_name} owns the ticket there. "
                "Switch workspaces when you want live follow-through."
            ),
            "created_at": created_at,
        }
    )
    return thread_id


def route_cross_workspace_ticket(handoff: dict[str, Any]) -> dict[str, Any]:
    """Create a target-workspace task, specialty-route it, and post team messages.

    Never raises for soft routing/comms failures — the handoff record remains the
    durable audit trail even when communication is partial.
    """
    handoff_id = str(handoff.get("handoff_id") or "").strip()
    source_id = str(handoff.get("source_workspace_id") or "").strip()
    target_id = str(handoff.get("target_workspace_id") or "").strip()
    task_text = str(handoff.get("task") or "").strip()
    reason = str(handoff.get("reason") or "").strip()
    if not handoff_id or not source_id or not target_id or not task_text:
        return handoff

    acceptance = (
        f"Complete the cross-workspace handoff from {_workspace_label(source_id)}. "
        "Leave a receipt on the target task board when done."
    )
    if reason:
        acceptance = f"{acceptance} Reason: {_truncate(reason, max_len=200)}"

    routed_role = ""
    routed_employee_id = ""
    routed_name = "Lead"
    try:
        decision = route_teammate_decision(
            workspace_id=target_id,
            prompt=task_text,
            use_model_tiebreak=False,
        )
        if decision.should_route and decision.employee is not None:
            routed_role = decision.employee.role
            routed_employee_id = decision.employee.employee_id
            routed_name = decision.employee.name
    except Exception:  # noqa: BLE001 — fall back to Lead
        logger.exception("cross-workspace specialty route failed for %s", handoff_id)

    if not routed_employee_id:
        lead = _lead_employee(target_id)
        if lead is not None:
            routed_role = "lead"
            routed_employee_id = lead["employee_id"]
            routed_name = lead["name"]

    try:
        task = task_store.create_task(
            workspace_id=target_id,
            goal=task_text,
            acceptance_criteria=acceptance,
            risk="normal",
            owner_role=routed_role or "lead",
        )
    except Exception:  # noqa: BLE001 — keep recorded handoff if ledger write fails
        logger.exception("cross-workspace target task create failed for %s", handoff_id)
        return handoff

    task_id = str(task.get("task_id") or "").strip()
    communication_thread_id = None
    source_communication_thread_id = None
    if routed_employee_id:
        try:
            communication_thread_id = _post_target_thread_messages(
                workspace_id=target_id,
                handoff_id=handoff_id,
                task_id=task_id,
                task_text=task_text,
                reason=reason,
                source_workspace_id=source_id,
                employee_id=routed_employee_id,
                employee_role=routed_role or "lead",
                employee_name=routed_name,
            )
        except Exception:  # noqa: BLE001 — task still exists without chat
            logger.exception("target handoff communication failed for %s", handoff_id)

    try:
        source_communication_thread_id = _post_source_ack(
            workspace_id=source_id,
            handoff_id=handoff_id,
            target_workspace_id=target_id,
            task_id=task_id,
            routed_name=routed_name,
            task_text=task_text,
        )
    except Exception:  # noqa: BLE001 — target ticket still valid
        logger.exception("source handoff ack failed for %s", handoff_id)

    updated = handoff_store.update_handoff(
        handoff_id,
        status="routed",
        target_task_id=task_id,
        routed_role=routed_role,
        routed_employee_id=routed_employee_id,
        communication_thread_id=communication_thread_id,
        source_communication_thread_id=source_communication_thread_id,
    )
    return updated or handoff
