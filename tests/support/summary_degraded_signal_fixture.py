"""Shared watch-summary degraded signal constants for contract alignment tests."""

from __future__ import annotations

from tests.support.bootstrap_signal_fixture import CONSISTENCY_FIELDS, consistency_tuple

SUMMARY_DEGRADED_SIGNAL_ID = "signal_runtime_summary_degraded"
SUMMARY_DEGRADED_WORKSPACE_ID = "workspace_alpha"

BOOTSTRAP_SUMMARY_DEGRADED_TITLE = "Bootstrap: runtime summary stale"
BOOTSTRAP_SUMMARY_DEGRADED_SUMMARY = (
    "Expected in local bootstrap when watch is connected but summary assembly is still thin."
)
BOOTSTRAP_SUMMARY_DEGRADED_BODY = (
    "In bootstrap dev mode, axon-watch stays connected while runtime summary data "
    "remains intentionally shallow. This is normal local scaffolding — not a production "
    "outage. Wire real watch connectors to replace this placeholder signal."
)

SUMMARY_DEGRADED_INBOX_ITEM = {
    "signal_id": SUMMARY_DEGRADED_SIGNAL_ID,
    "workspace_id": SUMMARY_DEGRADED_WORKSPACE_ID,
    "title": BOOTSTRAP_SUMMARY_DEGRADED_TITLE,
    "summary": BOOTSTRAP_SUMMARY_DEGRADED_SUMMARY,
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
    "title": BOOTSTRAP_SUMMARY_DEGRADED_TITLE,
    "body": BOOTSTRAP_SUMMARY_DEGRADED_BODY,
    "summary": BOOTSTRAP_SUMMARY_DEGRADED_SUMMARY,
    "dedupe_key": "watch:summary:degraded:workspace_alpha",
    "action_type": "open_dashboard",
    "action_payload": {"surface": "runtime-summary"},
    "correlation_ref": "corr_watch_summary_workspace_alpha",
    "delivery_state": "pending",
    "watch_rule": {
        "mode": "observe",
        "interrupts": False,
        "reason": "bootstrap_summary_stale",
    },
    "meta": {
        "signal_family": "watch_summary",
        "bootstrap_expected": True,
        "presentation": {
            "tone": "informational",
            "severity_display": "warning",
        },
    },
}

__all__ = [
    "BOOTSTRAP_SUMMARY_DEGRADED_BODY",
    "BOOTSTRAP_SUMMARY_DEGRADED_SUMMARY",
    "BOOTSTRAP_SUMMARY_DEGRADED_TITLE",
    "CONSISTENCY_FIELDS",
    "SUMMARY_DEGRADED_INBOX_ITEM",
    "SUMMARY_DEGRADED_SIGNAL_EVENT_STATIC",
    "SUMMARY_DEGRADED_SIGNAL_ID",
    "SUMMARY_DEGRADED_WORKSPACE_ID",
    "consistency_tuple",
]
