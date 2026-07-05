"""Inbox projections for connector probe failures."""

from __future__ import annotations

from app.signals.iso_time import utc_now_iso


def connector_inbox_item(record: dict[str, object]) -> dict[str, object] | None:
    status = str(record.get("status", "")).strip()
    if status == "ok":
        return None

    if not bool(record.get("required")):
        return None

    connector_id = str(record.get("connector_id", "")).strip()
    if not connector_id:
        return None

    display_name = str(record.get("display_name", connector_id)).strip()
    detail = str(record.get("detail", "")).strip()
    workspace_id = str(record.get("workspace_id", "workspace_axon_watch")).strip()
    now = utc_now_iso()
    severity = "high" if status == "degraded" else "critical"
    summary = detail or f"Connector {display_name} is {status}."

    return {
        "signal_id": f"signal_connector_{connector_id}_{status}",
        "workspace_id": workspace_id,
        "title": f"{display_name} connector {status}",
        "summary": summary,
        "severity": severity,
        "status": "open",
        "source": "connector",
        "created_at": now,
        "updated_at": now,
        "action_type": "investigate",
        "delivery_state": "pending",
    }


def connector_inbox_items(records: list[dict[str, object]]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for record in records:
        item = connector_inbox_item(record)
        if item is not None:
            items.append(item)
    return items
