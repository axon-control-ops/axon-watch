"""Persisted watch command records for operator-issued observation actions."""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import json
import os

from app.persistence import watch_store_sqlite


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
        connection.execute("DELETE FROM watch_commands")
        connection.commit()


def save_command(record: dict[str, object]) -> dict[str, object]:
    stored = deepcopy(record)
    command_id = str(stored["command_id"])
    updated_at = str(stored.get("updated_at", ""))
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO watch_commands (command_id, updated_at, record_json)
            VALUES (?, ?, ?)
            ON CONFLICT(command_id) DO UPDATE SET
              updated_at=excluded.updated_at,
              record_json=excluded.record_json
            """,
            (command_id, updated_at, json.dumps(stored)),
        )
        connection.commit()
    return deepcopy(stored)


def get_command(command_id: str) -> dict[str, object] | None:
    with _managed_connection() as connection:
        row = connection.execute(
            "SELECT record_json FROM watch_commands WHERE command_id = ?",
            (command_id.strip(),),
        ).fetchone()
    if row is None:
        return None
    return deepcopy(json.loads(str(row["record_json"])))


def update_command(command_id: str, **fields: object) -> dict[str, object] | None:
    record = get_command(command_id)
    if record is None:
        return None
    record.update(fields)
    return save_command(record)


def list_commands(*, limit: int = 50) -> dict[str, object]:
    max_limit = max(1, min(100, int(limit or 50)))
    with _managed_connection() as connection:
        count_row = connection.execute("SELECT COUNT(*) FROM watch_commands").fetchone()
        rows = connection.execute(
            """
            SELECT record_json
            FROM watch_commands
            ORDER BY updated_at DESC, command_id ASC
            LIMIT ?
            """,
            (max_limit,),
        ).fetchall()

    items = [json.loads(str(row["record_json"])) for row in rows]
    return {
        "items": items,
        "count": len(items),
        "total": int(count_row[0]) if count_row is not None else 0,
    }


def _observation_detail_from_command(record: dict[str, object]) -> str:
    """Surface receipt detail so observation never stops at bare failed/completed."""
    status = str(record.get("status", "")).strip()
    receipt = record.get("receipt")
    if not isinstance(receipt, dict):
        return ""

    if status == "failed":
        return str(receipt.get("error", "")).strip()

    result = receipt.get("result")
    if not isinstance(result, dict):
        return ""

    detail = str(result.get("detail", "")).strip()
    if detail:
        return detail

    connector_status = str(result.get("connector_status", "")).strip()
    if connector_status and connector_status not in {"ok", "completed"}:
        return connector_status

    summary_status = str(result.get("summary_status", "")).strip()
    if summary_status and summary_status != "ok":
        return summary_status

    return ""


def latest_command_snapshot() -> dict[str, object]:
    with _managed_connection() as connection:
        row = connection.execute(
            """
            SELECT record_json
            FROM watch_commands
            ORDER BY updated_at DESC, command_id ASC
            LIMIT 1
            """
        ).fetchone()

    if row is None:
        return {
            "last_command_id": "",
            "last_command_status": "",
            "last_command_at": "",
            "last_command_detail": "",
        }

    latest = json.loads(str(row["record_json"]))
    return {
        "last_command_id": str(latest.get("command_id", "")),
        "last_command_status": str(latest.get("status", "")),
        "last_command_at": str(latest.get("updated_at", "")),
        "last_command_detail": _observation_detail_from_command(latest),
    }
