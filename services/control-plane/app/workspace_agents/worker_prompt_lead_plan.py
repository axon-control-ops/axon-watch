"""Lead-plan evidence prompt block for continuous Lead shifts."""

from __future__ import annotations

from app.workspace_agents.lead_text import truncate_text as _truncate


def lead_plan_evidence_clause(
    *,
    workspace_id: str,
    goal: str,
    acceptance: str,
    task_id: str,
) -> str:
    """Embed durable Lead-plan receipts into Lead worker prompts.

    Lead follow-up shifts often run in disposable checkouts that cannot read the
    live control-plane sqlite database. If the prompt only says "advance plan X",
    the Lead must either hallucinate status or block. This packet gives the Lead
    the minimal, sanitized control-plane truth needed to choose the next handoff.
    """
    try:
        from app.workspace_agents import lead_plan_store
        from app.workspace_agents.lead_plan_control import extract_plan_id_from_goal
    except Exception:  # noqa: BLE001
        return ""

    plan_id = (
        extract_plan_id_from_goal(goal)
        or extract_plan_id_from_goal(acceptance)
        or lead_plan_store.plan_id_for_task(task_id)
        or ""
    )
    plan_id = str(plan_id or "").strip()
    if not plan_id:
        return ""

    try:
        plan = lead_plan_store.get_plan(plan_id)
    except Exception:  # noqa: BLE001
        plan = None
    if not isinstance(plan, dict):
        return (
            " Lead plan evidence packet: the leased task references "
            f"{plan_id}, but this control-plane session has no durable Lead plan "
            "record for that id. Do not queue a self-follow-up that repeats the "
            "same blocker; report to VAXON/operator that the plan ledger is missing "
            "or stale and include the plan id."
        )
    if str(plan.get("workspace_id") or "").strip() != str(workspace_id or "").strip():
        return (
            " Lead plan evidence packet: the referenced plan belongs to a different "
            "workspace than this leased task. Stop and report the workspace mismatch "
            "to VAXON/operator with the plan id; do not invent a handoff."
        )

    plan_body = plan.get("plan") if isinstance(plan.get("plan"), dict) else {}
    items = plan_body.get("items") if isinstance(plan_body.get("items"), list) else []
    try:
        links = lead_plan_store.plan_task_links(plan_id)
    except Exception:  # noqa: BLE001
        links = []
    link_by_key = {
        str(link.get("plan_key") or "").strip(): str(link.get("task_id") or "").strip()
        for link in links
        if isinstance(link, dict)
    }
    lines = [
        " Lead plan evidence packet (control-plane truth for this disposable shift):",
        f"- Plan: {plan_id} | status={str(plan.get('status') or 'unknown')} | goal={_truncate(str(plan.get('goal') or ''), max_len=180)}",
    ]
    try:
        from app.persistence import task_store

        for index, item in enumerate(items[:8], start=1):
            if not isinstance(item, dict):
                continue
            plan_key = str(item.get("id") or item.get("plan_key") or f"plan-{index:02d}").strip()
            role = str(item.get("owner_role") or item.get("role") or "specialist").strip()
            title = _truncate(
                str(item.get("title") or item.get("goal") or item.get("summary") or ""),
                max_len=130,
            )
            linked_task_id = link_by_key.get(plan_key, "")
            status = "unlinked"
            run_id = ""
            if linked_task_id:
                row = task_store.get_task(linked_task_id)
                if isinstance(row, dict):
                    status = str(row.get("status") or "unknown").strip() or "unknown"
                    run_id = str(row.get("run_id") or "").strip()
            run_bit = f" run={run_id}" if run_id else ""
            task_bit = f" task={linked_task_id}" if linked_task_id else " task=unlinked"
            lines.append(f"- {plan_key}: {role} {status}{task_bit}{run_bit} — {title}")
    except Exception:  # noqa: BLE001
        lines.append("- Task-link status unavailable in this prompt; use receipts below.")

    try:
        receipts = lead_plan_store.list_receipts(plan_id)[-6:]
    except Exception:  # noqa: BLE001
        receipts = []
    if receipts:
        lines.append("- Recent receipts:")
        for receipt in receipts:
            if not isinstance(receipt, dict):
                continue
            payload = receipt.get("payload") if isinstance(receipt.get("payload"), dict) else {}
            summary = (
                payload.get("summary")
                or payload.get("status")
                or payload.get("goal")
                or payload.get("phase")
                or payload.get("run_id")
                or ""
            )
            lines.append(
                f"  - {str(receipt.get('kind') or 'receipt')}: "
                f"{_truncate(str(summary or ''), max_len=160)}"
            )
    lines.append(
        "- Use this packet as the verified baseline; advance the parent plan by choosing "
        "assign / ship / escalate / report, and cite task/run receipts when available."
    )
    return "\n".join(lines)
