"""Canonical bootstrap signal owned by the watch service."""

from __future__ import annotations

from datetime import datetime, timezone

BOOTSTRAP_SIGNAL_ID = "signal_watch_bootstrap_ready"
BOOTSTRAP_WORKSPACE_ID = "workspace_bootstrap"
BOOTSTRAP_PROJECT_ID = "project_bootstrap"


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def bootstrap_signal_event() -> dict[str, object]:
    now = utc_now_iso()
    return {
        "event_id": "event_watch_bootstrap_opened",
        "signal_id": BOOTSTRAP_SIGNAL_ID,
        "event_type": "signal_opened",
        "source": "watch",
        "workspace_id": BOOTSTRAP_WORKSPACE_ID,
        "project_id": BOOTSTRAP_PROJECT_ID,
        "severity": "info",
        "status": "open",
        "title": "Watch bootstrap ready",
        "body": "The watch service emitted the first canonical bootstrap signal.",
        "summary": "Watch bootstrap signal is available.",
        "created_at": now,
        "updated_at": now,
        "occurred_at": now,
        "dedupe_key": "watch:bootstrap:ready",
        "action_type": "open_dashboard",
        "action_payload": {"surface": "inbox"},
        "correlation_ref": "corr_watch_bootstrap_ready",
        "delivery_state": "not_required",
        "meta": {"signal_family": "watch_bootstrap"},
    }


def bootstrap_inbox_item() -> dict[str, object]:
    event = bootstrap_signal_event()
    return {
        "signal_id": event["signal_id"],
        "workspace_id": event["workspace_id"],
        "title": event["title"],
        "summary": event["summary"],
        "severity": event["severity"],
        "status": event["status"],
        "source": event["source"],
        "updated_at": event["updated_at"],
        "action_type": event["action_type"],
    }
