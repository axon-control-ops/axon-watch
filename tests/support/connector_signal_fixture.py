"""Shared connector probe failure signal fixture for cross-surface consistency tests."""

from __future__ import annotations

CONNECTOR_SIGNAL_ID = "signal_connector_console_web_unavailable"
CONNECTOR_WORKSPACE_ID = "workspace_axon_watch"
CONNECTOR_PROBE_DETAIL = "status=503"

CONNECTOR_INBOX_ITEM = {
    "signal_id": CONNECTOR_SIGNAL_ID,
    "workspace_id": CONNECTOR_WORKSPACE_ID,
    "title": "Console web connector unavailable",
    "summary": CONNECTOR_PROBE_DETAIL,
    "severity": "critical",
    "status": "open",
    "source": "connector",
    "created_at": "2026-07-17T06:00:00Z",
    "updated_at": "2026-07-17T06:00:00Z",
    "action_type": "investigate",
    "delivery_state": "pending",
}

CONNECTOR_WATCH_INBOX = {
    "items": [CONNECTOR_INBOX_ITEM],
    "count": 1,
    "updated_at": "2026-07-17T06:00:00Z",
}

CONNECTOR_DEGRADED_SIGNAL_ID = "signal_connector_console_web_degraded"

CONNECTOR_DEGRADED_INBOX_ITEM = {
    "signal_id": CONNECTOR_DEGRADED_SIGNAL_ID,
    "workspace_id": CONNECTOR_WORKSPACE_ID,
    "title": "Console web connector degraded",
    "summary": "status=503",
    "severity": "high",
    "status": "open",
    "source": "connector",
    "created_at": "2026-07-17T06:00:00Z",
    "updated_at": "2026-07-17T06:00:00Z",
    "action_type": "investigate",
    "delivery_state": "pending",
}

CONNECTOR_DEGRADED_WATCH_INBOX = {
    "items": [CONNECTOR_DEGRADED_INBOX_ITEM],
    "count": 1,
    "updated_at": "2026-07-17T06:00:00Z",
}
