"""Shared DashPro Sentry monitor signal fixture for cross-surface consistency tests."""

from __future__ import annotations

SENTRY_MONITOR_SIGNAL_ID = "signal_monitor_dashpro_sentry_recent_issues_critical"
SENTRY_MONITOR_WORKSPACE_ID = "workspace_dashpro"

SENTRY_ISSUES = [
    {
        "id": "97620840",
        "short_id": "EDUDASHPRO-44",
        "title": "Error: [SignIn] Google Sign-In Error:",
        "level": "error",
        "count": 86,
        "permalink": "https://edudash-pro.sentry.io/issues/97620840/",
        "culprit": "error(index.android)",
    },
    {
        "id": "130828696",
        "short_id": "EDUDASHPRO-5Z",
        "title": "Error: cannot add postgres_changes callbacks after subscribe().",
        "level": "error",
        "count": 56,
        "permalink": "https://edudash-pro.sentry.io/issues/130828696/",
        "culprit": "on(index.android)",
    },
]

SENTRY_MONITOR_INBOX_ITEM = {
    "signal_id": SENTRY_MONITOR_SIGNAL_ID,
    "workspace_id": SENTRY_MONITOR_WORKSPACE_ID,
    "title": "DashPro Sentry critical",
    "summary": "Sentry returned 2 unresolved issue(s), 142 event(s); latest=Error: [SignIn] Google Sign-In Error:",
    "severity": "critical",
    "status": "open",
    "source": "watch",
    "created_at": "2026-07-17T06:00:00Z",
    "updated_at": "2026-07-17T06:00:00Z",
    "action_type": "investigate",
    "delivery_state": "pending",
    "meta": {
        "signal_family": "child_project_monitor",
        "workspace_label": "DashPro",
        "check_id": "dashpro_sentry_recent_issues",
        "check_type": "sentry_recent_issues",
        "monitor_status": "critical",
        "sentry_issues": SENTRY_ISSUES,
        "sentry_issue_count": len(SENTRY_ISSUES),
    },
}

SENTRY_MONITOR_WATCH_INBOX = {
    "items": [SENTRY_MONITOR_INBOX_ITEM],
    "count": 1,
    "updated_at": "2026-07-17T06:00:00Z",
}

POSTHOG_TRANSPORT_WARNING_SIGNAL_ID = (
    "signal_monitor_dashpro_posthog_recent_events_warning"
)

POSTHOG_TRANSPORT_WARNING_INBOX_ITEM = {
    "signal_id": POSTHOG_TRANSPORT_WARNING_SIGNAL_ID,
    "workspace_id": SENTRY_MONITOR_WORKSPACE_ID,
    "title": "DashPro PostHog warning",
    "summary": "PostHog API query failed: The read operation timed out",
    "severity": "warning",
    "status": "open",
    "source": "watch",
    "created_at": "2026-07-17T06:00:00Z",
    "updated_at": "2026-07-17T06:00:00Z",
    "action_type": "investigate",
    "delivery_state": "pending",
    "meta": {
        "signal_family": "child_project_monitor",
        "workspace_label": "DashPro",
        "check_id": "dashpro_posthog_recent_events",
        "check_type": "posthog_recent_events",
        "monitor_status": "warning",
    },
}

POSTHOG_TRANSPORT_WARNING_WATCH_INBOX = {
    "items": [POSTHOG_TRANSPORT_WARNING_INBOX_ITEM],
    "count": 1,
    "updated_at": "2026-07-17T06:00:00Z",
}

SENTRY_TRANSPORT_WARNING_SIGNAL_ID = (
    "signal_monitor_dashpro_sentry_recent_issues_warning"
)

SENTRY_TRANSPORT_WARNING_INBOX_ITEM = {
    "signal_id": SENTRY_TRANSPORT_WARNING_SIGNAL_ID,
    "workspace_id": SENTRY_MONITOR_WORKSPACE_ID,
    "title": "DashPro Sentry warning",
    "summary": "Sentry API query failed: The read operation timed out",
    "severity": "warning",
    "status": "open",
    "source": "watch",
    "created_at": "2026-07-17T06:00:00Z",
    "updated_at": "2026-07-17T06:00:00Z",
    "action_type": "investigate",
    "delivery_state": "pending",
    "meta": {
        "signal_family": "child_project_monitor",
        "workspace_label": "DashPro",
        "check_id": "dashpro_sentry_recent_issues",
        "check_type": "sentry_recent_issues",
        "monitor_status": "warning",
    },
}

SENTRY_TRANSPORT_WARNING_WATCH_INBOX = {
    "items": [SENTRY_TRANSPORT_WARNING_INBOX_ITEM],
    "count": 1,
    "updated_at": "2026-07-17T06:00:00Z",
}

# Sentry unresolved-issue threshold warning (monitor status=warning → severity=high).
SENTRY_THRESHOLD_WARNING_SIGNAL_ID = (
    "signal_monitor_dashpro_sentry_recent_issues_warning"
)

SENTRY_THRESHOLD_ISSUES = [
    {
        "id": "11111111",
        "short_id": "EDUDASHPRO-10",
        "title": "Error: session init timeout",
        "level": "error",
        "count": 12,
        "permalink": "https://edudash-pro.sentry.io/issues/11111111/",
        "culprit": "initSession(index.android)",
    },
]

SENTRY_THRESHOLD_WARNING_INBOX_ITEM = {
    "signal_id": SENTRY_THRESHOLD_WARNING_SIGNAL_ID,
    "workspace_id": SENTRY_MONITOR_WORKSPACE_ID,
    "title": "DashPro Sentry warning",
    "summary": (
        "Sentry returned 12 unresolved issue(s), 48 event(s); "
        "latest=Error: session init timeout"
    ),
    "severity": "high",
    "status": "open",
    "source": "watch",
    "created_at": "2026-07-17T06:00:00Z",
    "updated_at": "2026-07-17T06:00:00Z",
    "action_type": "investigate",
    "delivery_state": "pending",
    "meta": {
        "signal_family": "child_project_monitor",
        "workspace_label": "DashPro",
        "check_id": "dashpro_sentry_recent_issues",
        "check_type": "sentry_recent_issues",
        "monitor_status": "warning",
        "sentry_issues": SENTRY_THRESHOLD_ISSUES,
        "sentry_issue_count": len(SENTRY_THRESHOLD_ISSUES),
    },
}

SENTRY_THRESHOLD_WARNING_WATCH_INBOX = {
    "items": [SENTRY_THRESHOLD_WARNING_INBOX_ITEM],
    "count": 1,
    "updated_at": "2026-07-17T06:00:00Z",
}

# PostHog zero-recent-events warning (monitor status=warning → severity=high).
POSTHOG_THRESHOLD_WARNING_SIGNAL_ID = (
    "signal_monitor_dashpro_posthog_recent_events_warning"
)

POSTHOG_THRESHOLD_WARNING_INBOX_ITEM = {
    "signal_id": POSTHOG_THRESHOLD_WARNING_SIGNAL_ID,
    "workspace_id": SENTRY_MONITOR_WORKSPACE_ID,
    "title": "DashPro PostHog warning",
    "summary": "PostHog project is reachable but returned zero recent events",
    "severity": "high",
    "status": "open",
    "source": "watch",
    "created_at": "2026-07-17T06:00:00Z",
    "updated_at": "2026-07-17T06:00:00Z",
    "action_type": "investigate",
    "delivery_state": "pending",
    "meta": {
        "signal_family": "child_project_monitor",
        "workspace_label": "DashPro",
        "check_id": "dashpro_posthog_recent_events",
        "check_type": "posthog_recent_events",
        "monitor_status": "warning",
    },
}

POSTHOG_THRESHOLD_WARNING_WATCH_INBOX = {
    "items": [POSTHOG_THRESHOLD_WARNING_INBOX_ITEM],
    "count": 1,
    "updated_at": "2026-07-17T06:00:00Z",
}

# PostHog auth/access failure (monitor status=critical → severity=critical).
POSTHOG_CRITICAL_SIGNAL_ID = "signal_monitor_dashpro_posthog_recent_events_critical"

POSTHOG_CRITICAL_INBOX_ITEM = {
    "signal_id": POSTHOG_CRITICAL_SIGNAL_ID,
    "workspace_id": SENTRY_MONITOR_WORKSPACE_ID,
    "title": "DashPro PostHog critical",
    "summary": "PostHog API rejected the personal API key",
    "severity": "critical",
    "status": "open",
    "source": "watch",
    "created_at": "2026-07-17T06:00:00Z",
    "updated_at": "2026-07-17T06:00:00Z",
    "action_type": "investigate",
    "delivery_state": "pending",
    "meta": {
        "signal_family": "child_project_monitor",
        "workspace_label": "DashPro",
        "check_id": "dashpro_posthog_recent_events",
        "check_type": "posthog_recent_events",
        "monitor_status": "critical",
    },
}

POSTHOG_CRITICAL_WATCH_INBOX = {
    "items": [POSTHOG_CRITICAL_INBOX_ITEM],
    "count": 1,
    "updated_at": "2026-07-17T06:00:00Z",
}

# Supabase Storage quota critical (usage ≥90% or restriction → severity=critical).
SUPABASE_STORAGE_CRITICAL_SIGNAL_ID = (
    "signal_monitor_dashpro_supabase_storage_quota_critical"
)

SUPABASE_STORAGE_CRITICAL_INBOX_ITEM = {
    "signal_id": SUPABASE_STORAGE_CRITICAL_SIGNAL_ID,
    "workspace_id": SENTRY_MONITOR_WORKSPACE_ID,
    "title": "DashPro Supabase Storage critical",
    "summary": (
        "Supabase Storage 980 MB / 1.00 GB (98%). "
        "Top buckets: tts-audio 980 MB (10 files)"
    ),
    "severity": "critical",
    "status": "open",
    "source": "watch",
    "created_at": "2026-07-17T06:00:00Z",
    "updated_at": "2026-07-17T06:00:00Z",
    "action_type": "investigate",
    "delivery_state": "pending",
    "meta": {
        "signal_family": "child_project_monitor",
        "workspace_label": "DashPro",
        "check_id": "dashpro_supabase_storage_quota",
        "check_type": "supabase_storage_quota",
        "monitor_status": "critical",
    },
}

SUPABASE_STORAGE_CRITICAL_WATCH_INBOX = {
    "items": [SUPABASE_STORAGE_CRITICAL_INBOX_ITEM],
    "count": 1,
    "updated_at": "2026-07-17T06:00:00Z",
}

# Supabase Storage quota warning (usage ≥80% → severity=high).
SUPABASE_STORAGE_THRESHOLD_WARNING_SIGNAL_ID = (
    "signal_monitor_dashpro_supabase_storage_quota_warning"
)

SUPABASE_STORAGE_THRESHOLD_WARNING_INBOX_ITEM = {
    "signal_id": SUPABASE_STORAGE_THRESHOLD_WARNING_SIGNAL_ID,
    "workspace_id": SENTRY_MONITOR_WORKSPACE_ID,
    "title": "DashPro Supabase Storage warning",
    "summary": (
        "Supabase Storage 850 MB / 1.00 GB (85%). "
        "Top buckets: tts-audio 850 MB (10 files)"
    ),
    "severity": "high",
    "status": "open",
    "source": "watch",
    "created_at": "2026-07-17T06:00:00Z",
    "updated_at": "2026-07-17T06:00:00Z",
    "action_type": "investigate",
    "delivery_state": "pending",
    "meta": {
        "signal_family": "child_project_monitor",
        "workspace_label": "DashPro",
        "check_id": "dashpro_supabase_storage_quota",
        "check_type": "supabase_storage_quota",
        "monitor_status": "warning",
    },
}

SUPABASE_STORAGE_THRESHOLD_WARNING_WATCH_INBOX = {
    "items": [SUPABASE_STORAGE_THRESHOLD_WARNING_INBOX_ITEM],
    "count": 1,
    "updated_at": "2026-07-17T06:00:00Z",
}
