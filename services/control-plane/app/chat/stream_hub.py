"""In-process pub/sub for lane-B agent transcript streaming."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from threading import Lock
from typing import Any

_lock = Lock()
_queues: dict[str, list[asyncio.Queue[dict[str, Any] | None]]] = defaultdict(list)
_buffered_events: dict[str, list[dict[str, Any]]] = defaultdict(list)
_MAX_BUFFERED_EVENTS = 64


def publish_chat_stream_event(thread_id: str, payload: dict[str, Any]) -> None:
    clean_thread_id = str(thread_id or "").strip()
    if not clean_thread_id:
        return
    stored = dict(payload)
    with _lock:
        buffer = _buffered_events[clean_thread_id]
        buffer.append(stored)
        if len(buffer) > _MAX_BUFFERED_EVENTS:
            del buffer[: len(buffer) - _MAX_BUFFERED_EVENTS]
        queues = list(_queues.get(clean_thread_id, []))
    for queue in queues:
        try:
            queue.put_nowait(stored)
        except asyncio.QueueFull:
            pass


def close_chat_stream(thread_id: str) -> None:
    publish_chat_stream_event(thread_id, {"type": "chat_stream_close"})
    with _lock:
        queues = list(_queues.get(thread_id, []))
    for queue in queues:
        try:
            queue.put_nowait(None)
        except asyncio.QueueFull:
            pass


def register_chat_stream_queue(thread_id: str, queue: asyncio.Queue[dict[str, Any] | None]) -> None:
    clean_thread_id = str(thread_id or "").strip()
    if not clean_thread_id:
        return
    with _lock:
        _queues[clean_thread_id].append(queue)
        replay = list(_buffered_events.get(clean_thread_id, []))
    for payload in replay:
        try:
            queue.put_nowait(dict(payload))
        except asyncio.QueueFull:
            break


def unregister_chat_stream_queue(thread_id: str, queue: asyncio.Queue[dict[str, Any] | None]) -> None:
    clean_thread_id = str(thread_id or "").strip()
    if not clean_thread_id:
        return
    with _lock:
        _queues[clean_thread_id] = [item for item in _queues[clean_thread_id] if item is not queue]
        if not _queues[clean_thread_id]:
            _queues.pop(clean_thread_id, None)


def clear_chat_stream_buffer(thread_id: str) -> None:
    clean_thread_id = str(thread_id or "").strip()
    if not clean_thread_id:
        return
    with _lock:
        _buffered_events.pop(clean_thread_id, None)


def format_sse(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n".encode("utf-8")
