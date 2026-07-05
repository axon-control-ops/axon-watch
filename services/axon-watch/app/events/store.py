"""Persisted watch observation event log (bounded)."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
import uuid

from app.persistence import watch_store_sqlite
from app.signals.iso_time import utc_now_iso

_MAX_EVENTS = watch_store_sqlite.MAX_EVENTS


def _configured_db_path() -> str | None:
    return os.environ.get("AXON_WATCH_WATCH_SERVICE_DB")


@contextmanager
def _managed_connection():
    connection = watch_store_sqlite.connect(_configured_db_path())
    try:
        yield connection
    finally:
        connection.close()


def reset_store() -> None:
    with _managed_connection() as connection:
        connection.execute("DELETE FROM watch_events")
        connection.commit()


def _next_sequence(connection) -> int:
    row = connection.execute("SELECT COALESCE(MAX(sequence), 0) FROM watch_events").fetchone()
    return int(row[0]) + 1


def _trim_events(connection) -> None:
    connection.execute(
        """
        DELETE FROM watch_events
        WHERE event_id NOT IN (
            SELECT event_id
            FROM watch_events
            ORDER BY sequence DESC
            LIMIT ?
        )
        """,
        (_MAX_EVENTS,),
    )


def append_event(
    *,
    event_type: str,
    payload: dict[str, object] | None = None,
    command_id: str = "",
) -> dict[str, object]:
    event = {
        "event_id": f"event-{uuid.uuid4().hex[:16]}",
        "event_type": event_type,
        "occurred_at": utc_now_iso(),
        "command_id": command_id,
        "payload": payload or {},
    }
    with _managed_connection() as connection:
        sequence = _next_sequence(connection)
        connection.execute(
            """
            INSERT INTO watch_events (event_id, sequence, occurred_at, record_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                event["event_id"],
                sequence,
                event["occurred_at"],
                json.dumps(event),
            ),
        )
        _trim_events(connection)
        connection.commit()
    return event


def list_events(*, limit: int = 20, cursor: str = "") -> dict[str, object]:
    max_limit = max(1, min(100, int(limit or 20)))
    with _managed_connection() as connection:
        rows = connection.execute(
            """
            SELECT record_json
            FROM watch_events
            ORDER BY sequence DESC
            """
        ).fetchall()

    items = [json.loads(str(row["record_json"])) for row in rows]

    start_index = 0
    if cursor.strip():
        for index, item in enumerate(items):
            if item.get("event_id") == cursor.strip():
                start_index = index + 1
                break

    page = items[start_index : start_index + max_limit]
    next_cursor = ""
    if start_index + max_limit < len(items) and page:
        next_cursor = str(page[-1].get("event_id", ""))

    return {
        "items": page,
        "count": len(page),
        "next_cursor": next_cursor,
        "updated_at": utc_now_iso(),
    }


def events_summary() -> dict[str, object]:
    with _managed_connection() as connection:
        count_row = connection.execute("SELECT COUNT(*) FROM watch_events").fetchone()
        latest_row = connection.execute(
            """
            SELECT record_json
            FROM watch_events
            ORDER BY sequence DESC
            LIMIT 1
            """
        ).fetchone()

    events_count = int(count_row[0]) if count_row is not None else 0
    if events_count == 0 or latest_row is None:
        return {
            "events_count": 0,
            "last_event_at": "",
            "last_event_type": "",
        }

    latest = json.loads(str(latest_row["record_json"]))
    return {
        "events_count": events_count,
        "last_event_at": str(latest.get("occurred_at", "")),
        "last_event_type": str(latest.get("event_type", "")),
    }
