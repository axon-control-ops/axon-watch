"""SSE stream for watch observation events."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from starlette.responses import StreamingResponse

from app.events.store import list_events


def _format_sse(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n".encode("utf-8")


async def watch_events_stream() -> AsyncIterator[bytes]:
    last_seen = ""
    yield _format_sse({"type": "connected"})
    while True:
        snapshot = list_events(limit=5)
        items = snapshot.get("items", [])
        if isinstance(items, list) and items:
            newest = items[0]
            event_id = str(newest.get("event_id", ""))
            if event_id and event_id != last_seen:
                last_seen = event_id
                yield _format_sse({"type": "watch_event", "event": newest})
        await asyncio.sleep(2)


def watch_events_stream_response() -> StreamingResponse:
    return StreamingResponse(
        watch_events_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
