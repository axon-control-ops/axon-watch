"""Inbox, monitors, connectors, tunnel, and watch integration routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.adapters.watch_client import (
    fetch_watch_connectors,
    fetch_watch_delivery_receipts,
    fetch_watch_events,
    fetch_watch_monitors,
    fetch_watch_tunnel,
    get_watch_command,
    post_watch_command,
    post_watch_tunnel_action,
)
from app.inbox_projection import build_inbox_response
from app.inbox_signals import acknowledge_inbox_signals
from app.routes.schemas import AcknowledgeInboxSignalsRequest, WatchCommandRequest

router = APIRouter()


@router.get("/api/inbox")
def inbox() -> dict[str, object]:
    return build_inbox_response()


@router.post("/api/inbox/signals/acknowledge")
def inbox_signals_acknowledge(body: AcknowledgeInboxSignalsRequest) -> dict[str, object]:
    result = acknowledge_inbox_signals(body.signal_ids)
    if not result.get("accepted"):
        raise HTTPException(
            status_code=503,
            detail=str(result.get("error", "signal acknowledgement unavailable")),
        )
    return result


@router.get("/api/monitors")
def monitors_index() -> dict[str, object]:
    payload = fetch_watch_monitors()
    if payload is None:
        raise HTTPException(status_code=503, detail="watch monitors unavailable")
    return payload


@router.get("/api/connectors")
def connectors_index() -> dict[str, object]:
    payload = fetch_watch_connectors()
    if payload is None:
        raise HTTPException(status_code=503, detail="watch connectors unavailable")
    return payload


@router.get("/api/tunnel/status")
def tunnel_status_index() -> dict[str, object]:
    payload = fetch_watch_tunnel()
    if payload is None:
        raise HTTPException(status_code=503, detail="watch tunnel status unavailable")
    return payload


@router.post("/api/tunnel/start")
def tunnel_start_index() -> dict[str, object]:
    payload = post_watch_tunnel_action("start")
    if payload is None:
        raise HTTPException(status_code=503, detail="watch tunnel start unavailable")
    return payload


@router.post("/api/tunnel/stop")
def tunnel_stop_index() -> dict[str, object]:
    payload = post_watch_tunnel_action("stop")
    if payload is None:
        raise HTTPException(status_code=503, detail="watch tunnel stop unavailable")
    return payload


@router.post("/api/watch/commands")
def watch_commands_create(body: WatchCommandRequest) -> dict[str, object]:
    payload = post_watch_command(body.model_dump())
    if payload is None:
        raise HTTPException(status_code=503, detail="watch command submission unavailable")
    return payload


@router.get("/api/watch/commands/{command_id}")
def watch_commands_show(command_id: str) -> dict[str, object]:
    payload = get_watch_command(command_id)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"watch command not found: {command_id}")
    return payload


@router.get("/api/watch/events")
def watch_events_index(limit: int = 20, cursor: str = "") -> dict[str, object]:
    payload = fetch_watch_events(limit=limit, cursor=cursor)
    if payload is None:
        raise HTTPException(status_code=503, detail="watch events unavailable")
    return payload


@router.get("/api/delivery/receipts")
def delivery_receipts_index(limit: int = 20, cursor: str = "") -> dict[str, object]:
    payload = fetch_watch_delivery_receipts(limit=limit, cursor=cursor)
    if payload is None:
        raise HTTPException(status_code=503, detail="watch delivery receipts unavailable")
    return payload
