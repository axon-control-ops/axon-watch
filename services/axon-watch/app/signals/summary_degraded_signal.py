"""Canonical watch-summary degraded signal owned by the watch service."""

from __future__ import annotations

from app.signals.iso_time import utc_now_iso

SUMMARY_DEGRADED_SIGNAL_ID = "signal_runtime_summary_degraded"
SUMMARY_DEGRADED_WORKSPACE_ID = "workspace_alpha"
SUMMARY_DEGRADED_PROJECT_ID = "project_alpha"

# Copy tuned for bootstrap dev: watch is connected but summary assembly stays thin.
BOOTSTRAP_SUMMARY_DEGRADED_TITLE = "Bootstrap: runtime summary stale"
BOOTSTRAP_SUMMARY_DEGRADED_SUMMARY = (
    "Expected in local bootstrap when watch is connected but summary assembly is still thin."
)
BOOTSTRAP_SUMMARY_DEGRADED_BODY = (
    "In bootstrap dev mode, axon-watch stays connected while runtime summary data "
    "remains intentionally shallow. This is normal local scaffolding — not a production "
    "outage. Wire real watch connectors to replace this placeholder signal."
)


def summary_degraded_signal_event() -> dict[str, object]:
    now = utc_now_iso()
    return {
        "event_id": "event_signal_contract_opened",
        "signal_id": SUMMARY_DEGRADED_SIGNAL_ID,
        "event_type": "signal_opened",
        "source": "watch",
        "workspace_id": SUMMARY_DEGRADED_WORKSPACE_ID,
        "project_id": SUMMARY_DEGRADED_PROJECT_ID,
        "severity": "high",
        "status": "open",
        "title": BOOTSTRAP_SUMMARY_DEGRADED_TITLE,
        "body": BOOTSTRAP_SUMMARY_DEGRADED_BODY,
        "summary": BOOTSTRAP_SUMMARY_DEGRADED_SUMMARY,
        "created_at": now,
        "updated_at": now,
        "occurred_at": now,
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


def summary_degraded_inbox_item() -> dict[str, object]:
    event = summary_degraded_signal_event()
    return {
        "signal_id": event["signal_id"],
        "workspace_id": event["workspace_id"],
        "title": event["title"],
        "summary": event["summary"],
        "severity": event["severity"],
        "status": event["status"],
        "source": event["source"],
        "created_at": event["created_at"],
        "updated_at": event["updated_at"],
        "action_type": event["action_type"],
        "delivery_state": event["delivery_state"],
        "watch_rule": event["watch_rule"],
    }
