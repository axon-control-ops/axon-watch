"""Assemble the watch summary DTO for control-plane consumption."""

from __future__ import annotations

from app.connectors.summary import build_connectors_snapshot, probe_all_connectors
from app.delivery.store import delivery_summary
from app.commands.store import latest_command_snapshot
from app.events.store import events_summary
from app.signals.inbox_filters import summarize_actionable_inbox
from app.signals.store import get_inbox_snapshot


def build_watch_summary() -> dict[str, object]:
    connector_items = probe_all_connectors()
    connectors = build_connectors_snapshot(connector_items)
    inbox = get_inbox_snapshot(connector_records=connector_items)

    signal_items = inbox.get("items", [])
    if not isinstance(signal_items, list):
        signal_items = []

    signal_summary = summarize_actionable_inbox(
        [item for item in signal_items if isinstance(item, dict)]
    )
    open_count = int(signal_summary["open_count"])
    critical_count = int(signal_summary["critical_count"])
    high_count = int(signal_summary["high_count"])

    runtime_degraded = int(connectors.get("required_unavailable", 0)) > 0
    observation = {
        **events_summary(),
        **latest_command_snapshot(),
        **delivery_summary(),
    }

    return {
        "status": "degraded" if runtime_degraded else "ok",
        "signals": {
            "open_count": open_count,
            "critical_count": critical_count,
            "high_count": high_count,
        },
        "inbox": inbox,
        "connectors": {
            "configured": connectors.get("configured", 0),
            "ok": connectors.get("ok", 0),
            "degraded": connectors.get("degraded", 0),
            "unavailable": connectors.get("unavailable", 0),
            "required_unavailable": connectors.get("required_unavailable", 0),
        },
        "runtime": {
            "connected": True,
            "degraded": runtime_degraded,
        },
        "observation": observation,
        "updated_at": inbox.get("updated_at", connectors.get("updated_at", "")),
    }


def build_connectors_response() -> dict[str, object]:
    snapshot = build_connectors_snapshot()
    return {
        "items": snapshot.get("items", []),
        "count": snapshot.get("configured", 0),
        "summary": {
            "configured": snapshot.get("configured", 0),
            "ok": snapshot.get("ok", 0),
            "degraded": snapshot.get("degraded", 0),
            "unavailable": snapshot.get("unavailable", 0),
            "required_unavailable": snapshot.get("required_unavailable", 0),
        },
        "updated_at": snapshot.get("updated_at", ""),
    }
