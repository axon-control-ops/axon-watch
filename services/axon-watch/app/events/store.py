"""In-memory watch observation event log (bounded ring buffer)."""

from __future__ import annotations

import uuid
from collections import deque

from app.signals.iso_time import utc_now_iso

_MAX_EVENTS = 200
_EVENTS: deque[dict[str, object]] = deque(maxlen=_MAX_EVENTS)


def reset_store() -> None:
    _EVENTS.clear()


def append_event(
    *,
    event_type: str,
    payload: dict[str, object] | None = None,
    command_id: str = "",
) -> dict[str, object]:
    event = {
        "event_id": f"event-{uuid.uuid4().hex[:16]}",
        "event_type": event_type,
        "occurred_at": utc_now_iso(),
        "command_id": command_id,
        "payload": payload or {},
    }
    _EVENTS.append(event)
    return event


def list_events(*, limit: int = 20, cursor: str = "") -> dict[str, object]:
    max_limit = max(1, min(100, int(limit or 20)))
    items = list(_EVENTS)
    items.reverse()

    start_index = 0
    if cursor.strip():
        for index, item in enumerate(items):
            if item.get("event_id") == cursor.strip():
                start_index = index + 1
                break

    page = items[start_index : start_index + max_limit]
    next_cursor = ""
    if start_index + max_limit < len(items) and page:
        next_cursor = str(page[-1].get("event_id", ""))

    return {
        "items": page,
        "count": len(page),
        "next_cursor": next_cursor,
        "updated_at": utc_now_iso(),
    }


def events_summary() -> dict[str, object]:
    if not _EVENTS:
        return {
            "events_count": 0,
            "last_event_at": "",
            "last_event_type": "",
        }

    latest = _EVENTS[-1]
    return {
        "events_count": len(_EVENTS),
        "last_event_at": str(latest.get("occurred_at", "")),
        "last_event_type": str(latest.get("event_type", "")),
    }
