"""Persisted SQLite run storage for the control-plane run-state slice."""

from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
import json
import os
from typing import Any

from app.persistence import run_store_sqlite

_RUN_COLUMNS = (
    "run_id",
    "workspace_id",
    "lane_id",
    "mode",
    "status",
    "phase",
    "summary",
    "detail",
    "started_at",
    "updated_at",
    "ended_at",
    "can_stop",
    "can_resume",
    "can_approve",
    "can_review",
    "current_step",
    "history_ref",
)


def _configured_db_path() -> str | None:
    return os.environ.get("AXON_WATCH_CONTROL_PLANE_DB")


def _connection():
    return run_store_sqlite.connect(_configured_db_path())


@contextmanager
def _managed_connection():
    connection = _connection()
    try:
        yield connection
    finally:
        connection.close()


def _row_to_record(row: Any) -> dict[str, Any]:
    return {
        "run_id": row["run_id"],
        "workspace_id": row["workspace_id"],
        "lane_id": row["lane_id"],
        "mode": row["mode"],
        "status": row["status"],
        "phase": row["phase"],
        "summary": row["summary"],
        "detail": row["detail"],
        "started_at": row["started_at"],
        "updated_at": row["updated_at"],
        "ended_at": row["ended_at"],
        "can_stop": bool(row["can_stop"]),
        "can_resume": bool(row["can_resume"]),
        "can_approve": bool(row["can_approve"]),
        "can_review": bool(row["can_review"]),
        "current_step": row["current_step"],
        "history_ref": row["history_ref"],
    }


def _record_values(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        record["run_id"],
        record["workspace_id"],
        record["lane_id"],
        record["mode"],
        record["status"],
        record["phase"],
        record["summary"],
        record["detail"],
        record["started_at"],
        record["updated_at"],
        record["ended_at"],
        int(bool(record["can_stop"])),
        int(bool(record["can_resume"])),
        int(bool(record["can_approve"])),
        int(bool(record["can_review"])),
        record.get("current_step"),
        record["history_ref"],
    )


def reset_store() -> None:
    with _managed_connection() as connection:
        connection.execute("DELETE FROM operator_presence_settings")
        connection.execute("DELETE FROM run_history")
        connection.execute("DELETE FROM runs")
        connection.commit()


def save_run(record: dict[str, Any]) -> dict[str, Any]:
    stored = deepcopy(record)
    with _managed_connection() as connection:
        placeholders = ", ".join("?" for _ in _RUN_COLUMNS)
        update_clause = ", ".join(
            f"{column}=excluded.{column}" for column in _RUN_COLUMNS if column != "run_id"
        )
        connection.execute(
            f"""
            INSERT INTO runs ({", ".join(_RUN_COLUMNS)})
            VALUES ({placeholders})
            ON CONFLICT(run_id) DO UPDATE SET
              {update_clause}
            """,
            _record_values(stored),
        )
        connection.commit()
    return deepcopy(stored)


def get_run(run_id: str) -> dict[str, Any] | None:
    with _managed_connection() as connection:
        row = connection.execute(
            "SELECT * FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    return _row_to_record(row) if row is not None else None


def list_runs() -> list[dict[str, Any]]:
    with _managed_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM runs ORDER BY started_at ASC, run_id ASC"
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def append_transition(history_ref: str, transition: dict[str, Any]) -> None:
    payload = deepcopy(transition)
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    with _managed_connection() as connection:
        sequence = connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM run_history WHERE history_ref = ?",
            (history_ref,),
        ).fetchone()[0]
        connection.execute(
            """
            INSERT INTO run_history (history_ref, sequence, transition_json)
            VALUES (?, ?, ?)
            """,
            (history_ref, sequence, encoded),
        )
        connection.commit()


def list_history(history_ref: str) -> list[dict[str, Any]]:
    with _managed_connection() as connection:
        rows = connection.execute(
            """
            SELECT transition_json
            FROM run_history
            WHERE history_ref = ?
            ORDER BY sequence ASC
            """,
            (history_ref,),
        ).fetchall()
    return [json.loads(row["transition_json"]) for row in rows]
