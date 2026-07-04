"""Shared watch-summary degraded signal constants for contract alignment tests."""

from __future__ import annotations

from tests.support.bootstrap_signal_fixture import CONSISTENCY_FIELDS, consistency_tuple

SUMMARY_DEGRADED_SIGNAL_ID = "signal_runtime_summary_degraded"
SUMMARY_DEGRADED_WORKSPACE_ID = "workspace_alpha"

SUMMARY_DEGRADED_INBOX_ITEM = {
    "signal_id": SUMMARY_DEGRADED_SIGNAL_ID,
    "workspace_id": SUMMARY_DEGRADED_WORKSPACE_ID,
    "title": "Watch summary degraded",
    "summary": "Watch summary is degraded.",
    "severity": "high",
    "status": "open",
    "source": "watch",
    "created_at": "2026-07-03T15:01:00Z",
    "updated_at": "2026-07-03T15:02:00Z",
    "action_type": "open_dashboard",
}

SUMMARY_DEGRADED_SIGNAL_EVENT_STATIC = {
    "event_id": "event_signal_contract_opened",
    "signal_id": SUMMARY_DEGRADED_SIGNAL_ID,
    "event_type": "signal_opened",
    "source": "watch",
    "workspace_id": SUMMARY_DEGRADED_WORKSPACE_ID,
    "project_id": "project_alpha",
    "severity": "high",
    "status": "open",
    "title": "Watch summary degraded",
    "body": "The watch summary degraded and needs operator review.",
    "summary": "Watch summary is degraded.",
    "dedupe_key": "watch:summary:degraded:workspace_alpha",
    "action_type": "open_dashboard",
    "action_payload": {"surface": "runtime-summary"},
    "correlation_ref": "corr_watch_summary_workspace_alpha",
    "delivery_state": "pending",
    "meta": {"signal_family": "watch_summary"},
}

__all__ = [
    "CONSISTENCY_FIELDS",
    "SUMMARY_DEGRADED_INBOX_ITEM",
    "SUMMARY_DEGRADED_SIGNAL_EVENT_STATIC",
    "SUMMARY_DEGRADED_SIGNAL_ID",
    "SUMMARY_DEGRADED_WORKSPACE_ID",
    "consistency_tuple",
]
