"""Minimal FastAPI shell for the watch service bootstrap slice."""

from __future__ import annotations

import os

from fastapi import HTTPException, Query
from fastapi import FastAPI
from pydantic import BaseModel

from app.delivery.store import delivery_summary, list_receipts
from app.commands.executor import WatchCommandError
from app.commands.service import get_watch_command, submit_watch_command
from app.connectors.summary import probe_all_connectors
from app.events.store import list_events
from app.events.stream import watch_events_stream_response
from app.signals.store import get_inbox_snapshot
from app.signals.inbox_assembly import include_summary_degraded_signal
from app.watch_summary import build_connectors_response, build_watch_summary


def _state_dir() -> str:
    return os.environ.get("AXON_WATCH_STATE_DIR", "./.local/state")


class WatchCommandBody(BaseModel):
    command_id: str | None = None
    command_type: str
    target_type: str = ""
    target_id: str = ""
    requested_by: str = "control-plane"
    payload: dict[str, object] | None = None
    requested_at: str | None = None


app = FastAPI(
    title="Axon-X Watch Service",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)


@app.get("/internal/watch/health")
def health() -> dict[str, str]:
    return {
        "service": "axon-watch",
        "status": "ok",
        "mode": "bootstrap",
    }


@app.get("/internal/watch/readiness")
def readiness() -> dict[str, object]:
    connectors = build_connectors_response()
    summary = connectors.get("summary", {})
    connector_items = connectors.get("items")
    records = connector_items if isinstance(connector_items, list) else None
    degraded_expected = include_summary_degraded_signal(connector_records=records)
    return {
        "service": "axon-watch",
        "status": "ready",
        "mode": "bootstrap",
        "state_dir": _state_dir(),
        "dependencies": {
            "connectors_configured": summary.get("configured", 0),
            "connectors_ok": summary.get("ok", 0),
            "connectors_required_unavailable": summary.get("required_unavailable", 0),
        },
        "bootstrap_notes": {
            "summary_degraded_signal_expected": degraded_expected,
            "detail": (
                "Bootstrap may emit a stale runtime-summary signal until required "
                "connector probes are trusted; connector probes and watch "
                "commands/events are available on dedicated routes."
            ),
        },
    }


@app.get("/internal/watch/summary")
def summary() -> dict[str, object]:
    return build_watch_summary()


@app.get("/internal/watch/connectors")
def connectors() -> dict[str, object]:
    return build_connectors_response()


@app.get("/internal/watch/inbox")
def inbox() -> dict[str, object]:
    return get_inbox_snapshot(connector_records=probe_all_connectors())


@app.get("/internal/watch/delivery/receipts")
def delivery_receipts_index(
    limit: int = Query(20, ge=1, le=100),
    cursor: str = Query(""),
) -> dict[str, object]:
    return list_receipts(limit=limit, cursor=cursor)


@app.post("/internal/watch/commands")
def commands_create(body: WatchCommandBody) -> dict[str, object]:
    try:
        return submit_watch_command(body.model_dump())
    except WatchCommandError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/internal/watch/commands/{command_id}")
def commands_show(command_id: str) -> dict[str, object]:
    try:
        return get_watch_command(command_id)
    except WatchCommandError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/internal/watch/events")
def events_index(
    limit: int = Query(20, ge=1, le=100),
    cursor: str = Query(""),
) -> dict[str, object]:
    return list_events(limit=limit, cursor=cursor)


@app.get("/internal/watch/events/stream")
def events_stream():
    return watch_events_stream_response()
