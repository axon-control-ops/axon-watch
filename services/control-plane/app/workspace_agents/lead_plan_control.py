"""Controlling Lead plan + ship-intent helpers (sticky ownership / CI park)."""

from __future__ import annotations

import re
from typing import Any

from app.workspace_agents import lead_plan_store
from app.workspace_agents.lead_text import truncate_text

_SHIP_INTENT_RE = re.compile(
    r"\b("
    r"ota(?:\s+canary)?|"
    r"canary|"
    r"graduation|"
    r"ship(?:ping)?|"
    r"push\b.{0,40}\bcanary|"
    r"promote\b.{0,40}\bcanary"
    r")\b",
    re.IGNORECASE | re.DOTALL,
)

_PLAN_MARKER_RE = re.compile(r"\[plan\s+([^\]]+)\]", re.IGNORECASE)


def plan_marker(plan_id: str) -> str:
    cleaned = str(plan_id or "").strip()
    return f"[plan {cleaned}]" if cleaned else ""


def extract_plan_id_from_goal(goal: str) -> str | None:
    match = _PLAN_MARKER_RE.search(str(goal or ""))
    if not match:
        return None
    cleaned = match.group(1).strip()
    return cleaned or None


def controlling_lead_plan(
    workspace_id: str,
    *,
    plan_id: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any] | None:
    """Prefer explicit plan_id, then task→plan link, then active, then awaiting_engagement."""
    workspace = str(workspace_id or "").strip()
    if not workspace:
        return None

    def _usable(plan: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(plan, dict):
            return None
        if str(plan.get("workspace_id") or "").strip() != workspace:
            return None
        status = str(plan.get("status") or "").strip().lower()
        if status not in {"active", "awaiting_engagement"}:
            return None
        return plan

    explicit = str(plan_id or "").strip()
    if explicit:
        found = _usable(lead_plan_store.get_plan(explicit))
        if found is not None:
            return found

    linked = lead_plan_store.plan_id_for_task(str(task_id or "").strip())
    if linked:
        found = _usable(lead_plan_store.get_plan(linked))
        if found is not None:
            return found

    active = lead_plan_store.latest_active_plan(workspace)
    if active:
        return active

    awaiting = lead_plan_store.list_plans_by_status(
        "awaiting_engagement",
        workspace_id=workspace,
    )
    return awaiting[0] if awaiting else None


def plan_has_ship_intent(plan: dict[str, Any] | None) -> bool:
    if not isinstance(plan, dict):
        return False
    goal = str(plan.get("goal") or "")
    return bool(_SHIP_INTENT_RE.search(goal))


def controlling_ship_plan(workspace_id: str) -> dict[str, Any] | None:
    plan = controlling_lead_plan(workspace_id)
    if plan is None or not plan_has_ship_intent(plan):
        return None
    return plan


def sticky_lead_follow_up_goal(
    *,
    plan: dict[str, Any],
    employee_name: str,
    employee_role: str,
    phase: str,
    blockers: str = "",
    lead_next: str = "",
    run_id: str = "",
) -> str:
    plan_id = str(plan.get("plan_id") or "").strip()
    plan_goal = truncate_text(str(plan.get("goal") or ""), max_len=160) or "Lead plan"
    name = (employee_name or employee_role or "specialist").strip()
    role = (employee_role or "specialist").strip()
    status = "completed" if phase == "completed" else (phase or "ended")
    parts = [
        f'Lead: advance "{plan_goal}" toward Done {plan_marker(plan_id)}',
        f"— after {name} ({role}) {status}.",
    ]
    blocker = truncate_text(blockers, max_len=160)
    if blocker:
        parts.append(f"Blocker: {blocker}.")
    decision = truncate_text(lead_next, max_len=160)
    if decision:
        parts.append(f"Decision needed: {decision}.")
    if run_id:
        parts.append(f"[from run {run_id}]")
    return " ".join(parts)


def sticky_lead_follow_up_acceptance(*, plan: dict[str, Any]) -> str:
    plan_id = str(plan.get("plan_id") or "").strip()
    plan_goal = " ".join(str(plan.get("goal") or "").split()).strip() or "the Lead plan"
    return (
        f"Sole truth: advance plan {plan_id} — {plan_goal}. "
        "Specialist digs and CI findings are inputs, not the ask. "
        "Do not re-open a completed specialist dig unless that role still has an open plan item. "
        "Prefer assign / approve / ship steps that move the plan forward; "
        "escalate Decide for ship gates. Never invent status. End with Confidence: N/10."
    )


__all__ = [
    "controlling_lead_plan",
    "controlling_ship_plan",
    "extract_plan_id_from_goal",
    "plan_has_ship_intent",
    "plan_marker",
    "sticky_lead_follow_up_acceptance",
    "sticky_lead_follow_up_goal",
]
