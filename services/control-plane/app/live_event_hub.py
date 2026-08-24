"""In-process fan-out for operator live-event SSE subscribers."""

from __future__ import annotations

import asyncio
from typing import Any

_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
_connection_count = 0
_disconnect_count = 0


def subscribe() -> asyncio.Queue[dict[str, Any]]:
    global _connection_count
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    _subscribers.add(queue)
    _connection_count += 1
    return queue


def unsubscribe(queue: asyncio.Queue[dict[str, Any]]) -> None:
    global _disconnect_count
    if queue in _subscribers:
        _disconnect_count += 1
    _subscribers.discard(queue)


def subscriber_count() -> int:
    return len(_subscribers)


def live_event_telemetry() -> dict[str, int]:
    return {
        "connection_count": _connection_count,
        "disconnect_count": _disconnect_count,
        "subscriber_count": len(_subscribers),
    }


def broadcast_live_event(payload: dict[str, Any]) -> int:
    delivered = 0
    for queue in list(_subscribers):
        try:
            queue.put_nowait(payload)
            delivered += 1
        except Exception:
            continue
    return delivered
