"""Mission Control status projection for autonomous attention."""

from __future__ import annotations

from typing import Any, Callable

from app.persistence import autonomous_attention_store, task_store
from app.workspace_agents.autonomous_attention_recovery import (
    reconcile_recovered_failed_shift_decisions,
)


def build_autonomy_status_feed(
    *,
    workspace_id: str | None,
    collapse_pending: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
    latest_outcome: Callable[..., dict[str, Any] | None],
) -> dict[str, Any]:
    """Return Mission Control status and repair stale recovered-shift approvals."""
    from app.persistence import operator_presence_settings_store
    from app.workspace_agents.fleet_control import build_scheduler_status

    settings = operator_presence_settings_store.load_settings()
    mode = str(settings.get("autonomy_mode") or "manual").strip().lower()
    scheduler = build_scheduler_status()
    scoped_workspace = str(workspace_id or "").strip()
    receipts = autonomous_attention_store.list_receipts(
        limit=30,
        workspace_id=scoped_workspace or None,
    )
    for receipt in receipts:
        task_id = str(receipt.get("task_id") or "").strip()
        if not task_id:
            continue
        task = task_store.get_task(task_id)
        if task is None:
            continue
        payload = receipt.get("payload")
        if not isinstance(payload, dict):
            payload = {}
            receipt["payload"] = payload
        payload["task_status"] = str(task.get("status") or "")
        payload["terminal_outcome"] = str(task.get("terminal_outcome") or "")
    pending = collapse_pending(
        autonomous_attention_store.list_pending_decisions(
            limit=500,
            workspace_id=scoped_workspace or None,
        )
    )
    if scoped_workspace:
        reconcile_recovered_failed_shift_decisions(
            scoped_workspace,
            pending,
            latest_outcome=latest_outcome,
        )
        pending = collapse_pending(
            autonomous_attention_store.list_pending_decisions(
                limit=500,
                workspace_id=scoped_workspace,
            )
        )
    last_scan_key = f"last_scan:{scoped_workspace}" if scoped_workspace else "last_scan"
    last_scan = autonomous_attention_store.get_meta(last_scan_key) or {}
    return {
        "autonomy_mode": mode if mode in {"manual", "semi", "full"} else "manual",
        "autonomous_enabled": mode == "full",
        "effective_autonomy": mode == "full"
        and bool(scheduler.get("effective_enabled")),
        "scheduler": {
            "effective_enabled": bool(scheduler.get("effective_enabled")),
            "scheduler_enabled": bool(scheduler.get("scheduler_enabled")),
            "blocked_by_env": bool(scheduler.get("blocked_by_env")),
            "env_allowed": bool(scheduler.get("env_allowed")),
            "executing_count": int(scheduler.get("executing_count") or 0),
            "hard_killed": bool(scheduler.get("hard_killed")),
        },
        "last_scan": last_scan if isinstance(last_scan, dict) else {},
        "pending_critical_count": len(pending),
        "pending_critical_decisions": pending[:12],
        "recent_receipts": receipts[:20],
        "safety_contract": {
            "auto_allowed": [
                "inspect",
                "retry_idempotent_checks",
                "route_internal_handoffs",
                "create_bounded_specialist_tasks",
                "edit_disposable_worktrees",
                "run_tests",
            ],
            "requires_operator": [
                "critical_severity_mutation",
                "secrets_credentials",
                "destructive_filesystem_git_database",
                "production_deploy_release",
                "protected_merge_push",
                "external_public_communication",
                "permissions_policy_changes",
                "approval_gated_runs",
                "raising_usage_spend_caps",
            ],
        },
    }
