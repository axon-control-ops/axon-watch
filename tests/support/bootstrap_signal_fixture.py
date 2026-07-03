"""Shared bootstrap signal constants for cross-surface consistency tests."""

from __future__ import annotations

BOOTSTRAP_SIGNAL_ID = "signal_watch_bootstrap_ready"
BOOTSTRAP_WORKSPACE_ID = "workspace_bootstrap"

CONSISTENCY_FIELDS = ("signal_id", "severity", "status", "source")

BOOTSTRAP_INBOX_ITEM = {
    "signal_id": BOOTSTRAP_SIGNAL_ID,
    "workspace_id": BOOTSTRAP_WORKSPACE_ID,
    "title": "Watch bootstrap ready",
    "summary": "Watch bootstrap signal is available.",
    "severity": "info",
    "status": "open",
    "source": "watch",
    "updated_at": "2026-07-03T16:00:00Z",
    "action_type": "open_dashboard",
}

BOOTSTRAP_WATCH_INBOX = {
    "items": [BOOTSTRAP_INBOX_ITEM],
    "count": 1,
    "updated_at": "2026-07-03T16:00:00Z",
}


def consistency_tuple(item: dict[str, object]) -> tuple[object, object, object, object]:
    return tuple(item[field] for field in CONSISTENCY_FIELDS)
