"""Shared email triage signal fixture for cross-surface consistency tests."""

from __future__ import annotations

EMAIL_SIGNAL_ID = "signal_email_stub_urgent"
EMAIL_WORKSPACE_ID = "workspace_dashpro"

EMAIL_INBOX_ITEM = {
    "signal_id": EMAIL_SIGNAL_ID,
    "workspace_id": EMAIL_WORKSPACE_ID,
    "title": "Email needs follow-up: Urgent: DashPro deploy failed",
    "summary": "CTO — Respond to the blocker or investigate the issue.",
    "severity": "high",
    "status": "open",
    "source": "email",
    "created_at": "2026-07-13T12:00:00Z",
    "updated_at": "2026-07-13T12:00:00Z",
    "action_type": "investigate",
    "delivery_state": "pending",
    "meta": {
        "signal_family": "email_triage",
        "sender": "CTO <cto@example.com>",
        "subject": "Urgent: DashPro deploy failed",
        "snippet": "Please investigate the failing deploy today.",
        "recommended_action": "reply_or_investigate",
        "recommended_detail": "Respond to the blocker or investigate the issue.",
        "workspace_hints": ["DashPro"],
    },
}

EMAIL_WATCH_INBOX = {
    "items": [EMAIL_INBOX_ITEM],
    "count": 1,
    "updated_at": "2026-07-13T12:00:00Z",
}
