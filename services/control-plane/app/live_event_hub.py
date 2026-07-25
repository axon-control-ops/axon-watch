"""In-process fan-out for operator live-event SSE subscribers."""

from __future__ import annotations

import asyncio
from typing import Any

_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()


def subscribe() -> asyncio.Queue[dict[str, Any]]:
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    _subscribers.add(queue)
    return queue


def unsubscribe(queue: asyncio.Queue[dict[str, Any]]) -> None:
    _subscribers.discard(queue)


def broadcast_live_event(payload: dict[str, Any]) -> int:
    delivered = 0
    for queue in list(_subscribers):
        try:
            queue.put_nowait(payload)
            delivered += 1
        except Exception:
            continue
    return delivered
