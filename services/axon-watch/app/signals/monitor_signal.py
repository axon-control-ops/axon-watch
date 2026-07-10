"""Inbox projections for DashPro monitor check results."""

from __future__ import annotations

from app.signals.iso_time import utc_now_iso


def monitor_inbox_item(record: dict[str, object]) -> dict[str, object] | None:
    status = str(record.get("status", "")).strip()
    if status in {"ok", "skipped"}:
        return None

    check_id = str(record.get("check_id", "")).strip()
    if not check_id:
        return None

    service = str(record.get("service") or check_id).strip()
    detail = str(record.get("detail", "")).strip()
    workspace_id = str(record.get("workspace_id", "workspace_dashpro")).strip()
    workspace_label = str(record.get("workspace_label") or workspace_id).strip()
    severity = "high" if status == "warning" else "critical"
    now = utc_now_iso()
    sentry_issues = record.get("issues") if isinstance(record.get("issues"), list) else []
    meta: dict[str, object] = {
        "signal_family": "child_project_monitor",
        "workspace_label": workspace_label,
        "check_id": check_id,
        "check_type": record.get("check_type"),
        "monitor_status": status,
    }
    if sentry_issues:
        meta["sentry_issues"] = sentry_issues
        meta["sentry_issue_count"] = len(sentry_issues)

    return {
        "signal_id": f"signal_monitor_{check_id}_{status}",
        "workspace_id": workspace_id,
        "title": f"{workspace_label} {service} {status}",
        "summary": detail or f"{service} monitor reported {status}.",
        "severity": severity,
        "status": "open",
        "source": "watch",
        "created_at": now,
        "updated_at": now,
        "action_type": "investigate",
        "delivery_state": "pending",
        "meta": meta,
    }


def monitor_inbox_items(records: list[dict[str, object]]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for record in records:
        item = monitor_inbox_item(record)
        if item is not None:
            items.append(item)
    return items
