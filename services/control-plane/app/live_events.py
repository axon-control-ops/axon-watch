"""SSE live-event stub for runtime refresh hints."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from starlette.responses import StreamingResponse

REFRESH_INTERVAL_SECONDS = 10
PRESENCE_REFRESH_INTERVAL_SECONDS = 5


def _format_sse(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n".encode("utf-8")


async def live_events_stream() -> AsyncIterator[bytes]:
    yield _format_sse({"type": "connected"})
    tick = 0
    while True:
        await asyncio.sleep(PRESENCE_REFRESH_INTERVAL_SECONDS)
        tick += 1
        yield _format_sse({"type": "presence_refresh"})
        if tick * PRESENCE_REFRESH_INTERVAL_SECONDS >= REFRESH_INTERVAL_SECONDS:
            tick = 0
            yield _format_sse({"type": "runtime_refresh"})


def live_events_response() -> StreamingResponse:
    return StreamingResponse(
        live_events_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
