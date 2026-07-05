"""Persisted delivery receipt store (bounded)."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
import uuid

from app.persistence import watch_store_sqlite
from app.signals.iso_time import utc_now_iso

_MAX_RECEIPTS = watch_store_sqlite.MAX_RECEIPTS


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
        connection.execute("DELETE FROM watch_delivery_receipts")
        connection.execute("DELETE FROM watch_delivery_dedupe")
        connection.commit()


def _dedupe_key(signal_id: str, channel: str) -> str:
    return f"{signal_id.strip()}::{channel.strip().lower()}"


def has_successful_delivery(*, signal_id: str, channel: str) -> bool:
    key = _dedupe_key(signal_id, channel)
    with _managed_connection() as connection:
        row = connection.execute(
            "SELECT 1 FROM watch_delivery_dedupe WHERE dedupe_key = ?",
            (key,),
        ).fetchone()
    return row is not None


def _trim_receipts(connection) -> None:
    connection.execute(
        """
        DELETE FROM watch_delivery_receipts
        WHERE receipt_id NOT IN (
            SELECT receipt_id
            FROM watch_delivery_receipts
            ORDER BY attempted_at DESC, receipt_id ASC
            LIMIT ?
        )
        """,
        (_MAX_RECEIPTS,),
    )


def append_receipt(
    *,
    signal_id: str,
    event_id: str,
    channel: str,
    result: str,
    error: str = "",
    policy_reason: str = "",
) -> dict[str, object]:
    receipt = {
        "receipt_id": f"rcpt-{uuid.uuid4().hex[:16]}",
        "signal_id": signal_id.strip(),
        "event_id": event_id.strip(),
        "channel": channel.strip().lower(),
        "attempted_at": utc_now_iso(),
        "result": result.strip().lower(),
        "error": error.strip(),
        "policy_reason": policy_reason.strip(),
    }
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO watch_delivery_receipts (
                receipt_id, signal_id, channel, attempted_at, result, record_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                receipt["receipt_id"],
                receipt["signal_id"],
                receipt["channel"],
                receipt["attempted_at"],
                receipt["result"],
                json.dumps(receipt),
            ),
        )
        if receipt["result"] == "succeeded":
            connection.execute(
                """
                INSERT OR IGNORE INTO watch_delivery_dedupe (dedupe_key)
                VALUES (?)
                """,
                (_dedupe_key(signal_id, channel),),
            )
        _trim_receipts(connection)
        connection.commit()
    return receipt


def list_receipts(*, limit: int = 20, cursor: str = "") -> dict[str, object]:
    max_limit = max(1, min(100, int(limit or 20)))
    with _managed_connection() as connection:
        rows = connection.execute(
            """
            SELECT record_json
            FROM watch_delivery_receipts
            ORDER BY attempted_at DESC, receipt_id ASC
            """
        ).fetchall()

    items = [json.loads(str(row["record_json"])) for row in rows]

    start_index = 0
    if cursor.strip():
        for index, item in enumerate(items):
            if item.get("receipt_id") == cursor.strip():
                start_index = index + 1
                break

    page = items[start_index : start_index + max_limit]
    next_cursor = ""
    if start_index + max_limit < len(items) and page:
        next_cursor = str(page[-1].get("receipt_id", ""))

    return {
        "items": page,
        "count": len(page),
        "next_cursor": next_cursor,
        "updated_at": utc_now_iso(),
    }


def receipts_for_signal(signal_id: str) -> list[dict[str, object]]:
    target = signal_id.strip()
    with _managed_connection() as connection:
        rows = connection.execute(
            """
            SELECT record_json
            FROM watch_delivery_receipts
            WHERE signal_id = ?
            ORDER BY attempted_at ASC, receipt_id ASC
            """,
            (target,),
        ).fetchall()
    return [json.loads(str(row["record_json"])) for row in rows]


def delivery_summary() -> dict[str, object]:
    with _managed_connection() as connection:
        count_row = connection.execute("SELECT COUNT(*) FROM watch_delivery_receipts").fetchone()
        latest_row = connection.execute(
            """
            SELECT record_json
            FROM watch_delivery_receipts
            ORDER BY attempted_at DESC, receipt_id ASC
            LIMIT 1
            """
        ).fetchone()

    receipts_count = int(count_row[0]) if count_row is not None else 0
    if receipts_count == 0 or latest_row is None:
        return {
            "receipts_count": 0,
            "last_receipt_at": "",
            "last_receipt_result": "",
        }

    latest = json.loads(str(latest_row["record_json"]))
    return {
        "receipts_count": receipts_count,
        "last_receipt_at": str(latest.get("attempted_at", "")),
        "last_receipt_result": str(latest.get("result", "")),
    }
