"""Read-only Mission Control autonomy status feed."""

from __future__ import annotations

from typing import Any

from app.persistence import autonomous_attention_store, operator_presence_settings_store, task_store
from app.workspace_agents.fleet_control import build_scheduler_status


def _active_critical_signal_keys(workspace_id: str) -> set[str] | None:
    """Return live critical-signal receipt keys, or ``None`` when unknown.

    Attention receipts are durable by design, while monitor signals can be
    resolved independently.  The operator decision surface must not keep
    showing a receipt after its source alert is gone.  A missing snapshot is
    treated as unknown rather than hiding a possibly real decision.
    """
    try:
        from app.adapters.watch_client import fetch_watch_inbox

        inbox = fetch_watch_inbox(
            timeout_seconds=0.8,
            allow_stale=True,
            cached_only=False,
        )
    except Exception:  # noqa: BLE001 - decision status must remain available
        return None
    rows = inbox.get("items") if isinstance(inbox, dict) else None
    if not isinstance(rows, list):
        return None

    keys: set[str] = set()
    workspace = workspace_id.strip()
    for signal in rows:
        if not isinstance(signal, dict):
            continue
        signal_workspace = str(signal.get("workspace_id") or "").strip()
        if workspace and signal_workspace and signal_workspace != workspace:
            continue
        if str(signal.get("status") or "open").strip().lower() not in {"", "open"}:
            continue
        if str(signal.get("severity") or "").strip().lower() != "critical":
            continue
        signal_id = str(signal.get("signal_id") or "").strip()
        if signal_id:
            keys.add(f"signal:{workspace}:{signal_id}:critical")
    return keys


def _pending_decision_is_current(
    receipt: dict[str, Any],
    *,
    active_critical_keys: set[str] | None,
) -> bool:
    """Hide a critical receipt when its originating signal is no longer open."""
    if str(receipt.get("kind") or "").strip().lower() != "critical_signal":
        return True
    if active_critical_keys is None:
        return True
    dedupe_key = str(receipt.get("dedupe_key") or "").strip()
    # Older/non-signal critical receipts may represent a real guarded action.
    # Only filter the receipt shape that was created from a monitor signal.
    if not dedupe_key.startswith("signal:"):
        return True
    return dedupe_key in active_critical_keys


def build_autonomy_status_feed(*, workspace_id: str | None = None) -> dict[str, Any]:
    """Read-only status for Mission Control autonomy control."""
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
    pending = autonomous_attention_store.list_pending_decisions(
        limit=500,
        workspace_id=scoped_workspace or None,
    )
    active_critical_keys = _active_critical_signal_keys(scoped_workspace)
    pending = [
        receipt
        for receipt in pending
        if _pending_decision_is_current(
            receipt,
            active_critical_keys=active_critical_keys,
        )
    ]
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


__all__ = ["build_autonomy_status_feed"]
