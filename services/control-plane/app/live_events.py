"""SSE live-event stream for runtime refresh hints and dev triggers."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from starlette.responses import StreamingResponse

from app.live_event_hub import subscribe, unsubscribe

REFRESH_INTERVAL_SECONDS = 30
PRESENCE_REFRESH_INTERVAL_SECONDS = 60
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


def broadcast_material_change(
    *,
    signal_id: str | None = None,
    receipt_id: str | None = None,
) -> int:
    """Event-driven proactive invalidation — not a timer heartbeat."""
    from app.live_event_hub import broadcast_live_event

    payload: dict[str, object] = {"type": "material_change"}
    if signal_id:
        payload["signal_id"] = signal_id
    if receipt_id:
        payload["receipt_id"] = receipt_id
    return broadcast_live_event(payload)


def broadcast_spoken_line(
    *,
    line: str,
    receipt_id: str,
    workspace_id: str | None = None,
    kind: str = "lead_takeover",
    speaker_name: str = "Lead",
    speaker_role: str = "lead",
    speaker_employee_id: str | None = None,
) -> int:
    """Explicit spoken interrupt — console speaks ``line`` as the named speaker."""
    from app.live_event_hub import broadcast_live_event

    cleaned = " ".join(str(line or "").strip().split())
    if not cleaned:
        return 0
    payload: dict[str, object] = {
        "type": "spoken_line",
        "line": cleaned[:1200],
        "receipt_id": str(receipt_id or "").strip() or f"spoken_{kind}",
        "kind": str(kind or "lead_takeover").strip() or "lead_takeover",
        "speaker_name": str(speaker_name or "Lead").strip() or "Lead",
        "speaker_role": str(speaker_role or "lead").strip() or "lead",
    }
    if workspace_id:
        payload["workspace_id"] = str(workspace_id).strip()
    employee_id = str(speaker_employee_id or "").strip()
    if employee_id:
        payload["speaker_employee_id"] = employee_id
    return broadcast_live_event(payload)
