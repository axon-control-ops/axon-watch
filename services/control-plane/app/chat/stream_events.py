"""SSE stream for lane-B agent transcript updates."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from starlette.responses import StreamingResponse

from app.chat.stream_hub import format_sse, register_chat_stream_queue, unregister_chat_stream_queue


async def chat_thread_stream(thread_id: str) -> AsyncIterator[bytes]:
    clean_thread_id = str(thread_id or "").strip()
    queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue(maxsize=512)
    register_chat_stream_queue(clean_thread_id, queue)
    try:
        yield format_sse({"type": "connected", "thread_id": clean_thread_id})
        while True:
            payload = await queue.get()
            if payload is None:
                break
            yield format_sse(payload)
            if payload.get("type") == "chat_stream_close":
                break
    finally:
        unregister_chat_stream_queue(clean_thread_id, queue)


def chat_thread_stream_response(thread_id: str) -> StreamingResponse:
    return StreamingResponse(
        chat_thread_stream(thread_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
