"""SSE live-event stream for runtime refresh hints and dev triggers."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from starlette.responses import StreamingResponse

from app.live_event_hub import subscribe, unsubscribe

REFRESH_INTERVAL_SECONDS = 10
PRESENCE_REFRESH_INTERVAL_SECONDS = 5
_TICK_SECONDS = 1


def _format_sse(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n".encode("utf-8")


async def live_events_stream() -> AsyncIterator[bytes]:
    queue = subscribe()
    try:
        yield _format_sse({"type": "connected"})
        tick = 0
        while True:
            while True:
                try:
                    payload = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                yield _format_sse(payload)

            await asyncio.sleep(_TICK_SECONDS)
            tick += 1
            if tick % PRESENCE_REFRESH_INTERVAL_SECONDS == 0:
                yield _format_sse({"type": "presence_refresh"})
            if tick % REFRESH_INTERVAL_SECONDS == 0:
                yield _format_sse({"type": "runtime_refresh"})
    finally:
        unsubscribe(queue)


def live_events_response() -> StreamingResponse:
    return StreamingResponse(
        live_events_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
