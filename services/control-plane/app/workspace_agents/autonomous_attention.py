"""Bounded Mission Control attend loop for Full autonomy.

Scans failed shifts, monitors/connectors, top signals, and open handoffs.
Safe items become deduped specialist tasks; critical/dangerous items become
operator-gated receipts (never auto-leased).
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

from app.persistence import autonomous_attention_store, handoff_store, task_store
from app.workspace_agents.autonomous_attention_policy import classify_attention_item
from app.workspace_agents.autonomous_attention_findings import (
    collect_attend_findings,
    collect_handoff_findings,
    collect_signal_findings,
)
from app.workspace_agents.lead_checkin_assign import (
    ASSIGN_GOAL_PREFIX,
    ATTEND_GOAL_PREFIX,
    SPECIALIST_ROLES,
    LeadCheckinFinding,
)
from app.workspace_agents.autonomous_attention_status import build_autonomy_status_feed
from app.workspace_agents.lead_team_checkin import run_lead_team_checkin

logger = logging.getLogger(__name__)

DEFAULT_MAX_DISPATCH_PER_TICK = 3
DEFAULT_MAX_ESCALATIONS_PER_TICK = 5
_ATTEND_ENQUEUE_LOCK = threading.Lock()


def _open_attend_tasks(workspace_id: str) -> list[dict[str, Any]]:
    openish: list[dict[str, Any]] = []
    for status in ("open", "leased"):
        openish.extend(
            task_store.list_tasks(workspace_id=workspace_id, status=status, limit=200)
        )
    return [
        row
        for row in openish
        if str(row.get("goal") or "").startswith((ASSIGN_GOAL_PREFIX, ATTEND_GOAL_PREFIX))
    ]


def _already_tracked(dedupe_key: str, existing: list[dict[str, Any]]) -> bool:
    needle = dedupe_key.lower()
    if not needle:
        return False
    if autonomous_attention_store.has_recent_dedupe_key(needle):
        return True
    for row in existing:
        goal = str(row.get("goal") or "").lower()
        criteria = str(row.get("acceptance_criteria") or "").lower()
        if needle in goal or needle in criteria:
            return True
    return False


def enqueue_attend_actions(
    *,
    workspace_id: str,
    findings: list[LeadCheckinFinding],
    max_dispatch: int = DEFAULT_MAX_DISPATCH_PER_TICK,
    max_escalations: int = DEFAULT_MAX_ESCALATIONS_PER_TICK,
) -> dict[str, Any]:
    """Serialize scheduler/manual scans so dedupe+create is atomic in-process."""
    with _ATTEND_ENQUEUE_LOCK:
        return _enqueue_attend_actions(
            workspace_id=workspace_id,
            findings=findings,
            max_dispatch=max_dispatch,
            max_escalations=max_escalations,
        )


def _enqueue_attend_actions(
    *,
    workspace_id: str,
    findings: list[LeadCheckinFinding],
    max_dispatch: int = DEFAULT_MAX_DISPATCH_PER_TICK,
    max_escalations: int = DEFAULT_MAX_ESCALATIONS_PER_TICK,
) -> dict[str, Any]:
    """Create safe specialist tasks and escalate gated items with receipts."""
    workspace = workspace_id.strip()
    created: list[dict[str, Any]] = []
    escalated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    if not workspace:
        return {"created_tasks": created, "escalated": escalated, "skipped": skipped}

    existing = _open_attend_tasks(workspace)
    remaining_budget = max(0, int(max_dispatch))
    escalation_budget = max(0, int(max_escalations))
    priority = {
        "critical_signal": 0,
        "operator_blocker": 1,
        "warning_signal": 2,
        "high_signal": 2,
        "open_handoff": 3,
        "failed_shift": 4,
        "monitor_alert": 5,
        "connector_degraded": 6,
    }
    ordered = sorted(findings, key=lambda item: (priority.get(item.kind, 9), item.dedupe_key))
    for finding in ordered:
        policy = classify_attention_item(
            kind=finding.kind,
            title=finding.title,
            detail=finding.detail,
            escalate_only=finding.escalate_only,
            severity="critical" if finding.kind == "critical_signal" else "",
            dedupe_key=finding.dedupe_key,
        )
        if _already_tracked(finding.dedupe_key, existing + created):
            skipped.append({"dedupe_key": finding.dedupe_key, "reason": "deduped"})
            continue

        if policy.decision == "skip":
            skipped.append(
                {
                    "dedupe_key": finding.dedupe_key,
                    "reason": policy.reason or "policy_skip",
                }
            )
            continue

        if policy.decision != "dispatch" or policy.ask_operator:
            if escalation_budget <= 0:
                skipped.append({"dedupe_key": finding.dedupe_key, "reason": "escalation_cap"})
                continue
            receipt = autonomous_attention_store.append_receipt(
                kind=finding.kind,
                decision="escalate",
                tier=policy.tier,
                risk=policy.risk,
                title=finding.title,
                detail=finding.detail,
                dedupe_key=finding.dedupe_key,
                workspace_id=workspace,
                ask_operator=True,
                payload={
                    "owner_role": finding.owner_role,
                    "reason": policy.reason,
                    "finding_kind": finding.kind,
                },
            )
            escalated.append(receipt)
            escalation_budget -= 1
            continue

        if remaining_budget <= 0:
            skipped.append({"dedupe_key": finding.dedupe_key, "reason": "dispatch_cap"})
            continue
        if finding.owner_role not in SPECIALIST_ROLES:
            skipped.append({"dedupe_key": finding.dedupe_key, "reason": "no_owner"})
            continue
        try:
            record = task_store.create_task(
                workspace_id=workspace,
                goal=(
                    f"{ATTEND_GOAL_PREFIX} {finding.title}. "
                    f"Investigate and fix with receipts. [{finding.dedupe_key}]"
                ),
                acceptance_criteria=(
                    f"Resolve: {finding.detail}. "
                    "Stay inside disposable worker isolation. "
                    "Do not touch secrets, production, protected merges, or spend caps. "
                    "Never invent receipts; verify before claiming done. "
                    "End with Confidence: N/10. "
                    f"dedupe={finding.dedupe_key}"
                ),
                risk=policy.risk,
                owner_role=finding.owner_role,
                attempt_budget=2,
            )
        except task_store.TaskLedgerError as exc:
            logger.warning("attend loop could not create task: %s", exc)
            skipped.append({"dedupe_key": finding.dedupe_key, "reason": str(exc)})
            continue
        if finding.kind == "open_handoff" and finding.dedupe_key.startswith("handoff:"):
            handoff_id = finding.dedupe_key.removeprefix("handoff:")
            handoff_store.update_handoff(
                handoff_id,
                status="routed",
                target_task_id=str(record.get("task_id") or "") or None,
                routed_role=finding.owner_role,
            )
        autonomous_attention_store.append_receipt(
            kind=finding.kind,
            decision="dispatch",
            tier=policy.tier,
            risk=policy.risk,
            title=finding.title,
            detail=finding.detail,
            dedupe_key=finding.dedupe_key,
            workspace_id=workspace,
            task_id=str(record.get("task_id") or "") or None,
            ask_operator=False,
            payload={"owner_role": finding.owner_role},
        )
        created.append(record)
        remaining_budget -= 1

    return {"created_tasks": created, "escalated": escalated, "skipped": skipped}


def resolve_autonomy_decision(
    receipt_id: str,
    *,
    resolution: str,
) -> dict[str, Any]:
    """Approve a gated exact task or reject it; both paths are durable."""
    choice = str(resolution or "").strip().lower()
    if choice not in {"approved", "rejected"}:
        raise ValueError("resolution must be approved or rejected")
    receipt = autonomous_attention_store.begin_decision_resolution(receipt_id)
    if choice == "rejected":
        try:
            return autonomous_attention_store.complete_decision_resolution(
                receipt_id,
                resolution="rejected",
            )
        except Exception:
            autonomous_attention_store.release_decision_resolution(receipt_id)
            raise

    payload = receipt.get("payload") if isinstance(receipt.get("payload"), dict) else {}
    owner_role = str(payload.get("owner_role") or "watcher").strip().lower()
    if owner_role not in SPECIALIST_ROLES:
        owner_role = "watcher"
    workspace_id = str(receipt.get("workspace_id") or "").strip()
    if not workspace_id:
        autonomous_attention_store.release_decision_resolution(receipt_id)
        raise ValueError("autonomy decision is missing workspace_id")
    dedupe_key = str(receipt.get("dedupe_key") or receipt_id).strip()
    task: dict[str, Any] | None = None
    try:
        task = task_store.create_task(
            workspace_id=workspace_id,
            goal=(
                f"{ATTEND_GOAL_PREFIX} Operator approved: "
                f"{str(receipt.get('title') or receipt.get('kind') or 'guarded action')}. "
                f"[{dedupe_key}]"
            ),
            acceptance_criteria=(
                f"Exact approved effect: {str(receipt.get('detail') or receipt.get('title') or '')}. "
                f"Approval receipt={receipt_id}. Stay inside disposable worker isolation. "
                "Report receipts and end with Confidence: N/10."
            ),
            risk="approved",
            owner_role=owner_role,
            approval_receipt_id=receipt_id,
            attempt_budget=1,
        )
        return autonomous_attention_store.complete_decision_resolution(
            receipt_id,
            resolution="approved",
            task_id=str(task.get("task_id") or "") or None,
        )
    except Exception:
        if task is not None:
            try:
                task_store.cancel_task(
                    str(task.get("task_id") or ""),
                    terminal_outcome="approval resolution failed",
                )
            except task_store.TaskLedgerError:
                logger.exception("could not cancel failed approved task")
        autonomous_attention_store.release_decision_resolution(receipt_id)
        raise


def run_autonomous_attention_scan(
    *,
    workspace_ids: list[str] | None = None,
    max_dispatch_per_workspace: int = DEFAULT_MAX_DISPATCH_PER_TICK,
    max_escalations_per_workspace: int = DEFAULT_MAX_ESCALATIONS_PER_TICK,
    include_lead_checkin: bool = True,
    monitors_payload: dict[str, Any] | None = None,
    connectors_payload: dict[str, Any] | None = None,
    signals: list[dict[str, Any]] | None = None,
    handoffs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Tick Full-autonomy attend across company workspaces."""
    from app.workspace_agents.config_loader import load_workspace_agent_configs

    _configs, _defaults, companies, _staffing = load_workspace_agent_configs()
    targets = workspace_ids or sorted(companies.keys())
    result: dict[str, Any] = {
        "work_source": "autonomous_attention",
        "checked_workspaces": [],
        "created_tasks": [],
        "escalated": [],
        "skipped": [],
        "lead_checkin": None,
    }

    if include_lead_checkin:
        try:
            result["lead_checkin"] = run_lead_team_checkin(
                workspace_ids=targets,
                monitors_payload=monitors_payload,
                connectors_payload=connectors_payload,
                # Assignments happen in enqueue_attend_actions to keep one policy path.
                max_assignments_per_workspace=0,
            )
        except Exception:  # noqa: BLE001
            logger.exception("lead check-in during attend scan failed")
            result["lead_checkin"] = {"error": "lead_checkin_failed"}

    for workspace_id in targets:
        workspace = str(workspace_id or "").strip()
        if not workspace or workspace not in companies:
            continue
        findings = collect_attend_findings(
            workspace,
            monitors_payload=monitors_payload,
            connectors_payload=connectors_payload,
            signals=signals,
            handoffs=handoffs,
        )
        actions = enqueue_attend_actions(
            workspace_id=workspace,
            findings=findings,
            max_dispatch=max_dispatch_per_workspace,
            max_escalations=max_escalations_per_workspace,
        )
        result["checked_workspaces"].append(workspace)
        result["created_tasks"].extend(actions["created_tasks"])
        result["escalated"].extend(actions["escalated"])
        result["skipped"].extend(actions["skipped"])
        autonomous_attention_store.set_meta(
            f"last_scan:{workspace}",
            {
                "workspace_id": workspace,
                "scanned_at": datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z"),
                "created_count": len(actions["created_tasks"]),
                "escalated_count": len(actions["escalated"]),
                "skipped_count": len(actions["skipped"]),
            },
        )

    autonomous_attention_store.set_meta(
        "last_scan",
        {
            "scanned_at": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "checked_workspaces": result["checked_workspaces"],
            "created_count": len(result["created_tasks"]),
            "escalated_count": len(result["escalated"]),
            "skipped_count": len(result["skipped"]),
        },
    )
    autonomous_attention_store.append_receipt(
        kind="scan",
        decision="dispatch",
        tier="auto_safe",
        risk="normal",
        title="Autonomous attend scan",
        detail=(
            f"checked={len(result['checked_workspaces'])} "
            f"dispatched={len(result['created_tasks'])} "
            f"escalated={len(result['escalated'])}"
        ),
        dedupe_key="",
        ask_operator=False,
        payload={
            "checked_workspaces": result["checked_workspaces"],
            "created_count": len(result["created_tasks"]),
            "escalated_count": len(result["escalated"]),
        },
    )
    return result


__all__ = [
    "ATTEND_GOAL_PREFIX",
    "build_autonomy_status_feed",
    "collect_attend_findings",
    "collect_handoff_findings",
    "collect_signal_findings",
    "enqueue_attend_actions",
    "resolve_autonomy_decision",
    "run_autonomous_attention_scan",
]
