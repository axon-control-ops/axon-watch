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
    "employee_role",
    "task_id",
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
    keys = set(row.keys())
    employee_role = row["employee_role"] if "employee_role" in keys else None
    task_id = row["task_id"] if "task_id" in keys else None
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
        "employee_role": (str(employee_role).strip() if employee_role else None) or None,
        "task_id": (str(task_id).strip() if task_id else None) or None,
    }


def _record_values(record: dict[str, Any]) -> tuple[Any, ...]:
    employee_role = record.get("employee_role")
    cleaned_role = str(employee_role).strip() if employee_role else None
    task_id = record.get("task_id")
    cleaned_task = str(task_id).strip() if task_id else None
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
        cleaned_role or None,
        cleaned_task or None,
    )


def reset_store() -> None:
    with _managed_connection() as connection:
        connection.execute("DELETE FROM operator_presence_settings")
        connection.execute("DELETE FROM email_operator_settings")
        connection.execute("DELETE FROM worker_scheduler_settings")
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


def delete_run(run_id: str) -> bool:
    """Remove one run and its history. Returns False when the run does not exist."""
    cleaned = str(run_id or "").strip()
    if not cleaned:
        return False
    with _managed_connection() as connection:
        row = connection.execute(
            "SELECT history_ref FROM runs WHERE run_id = ?",
            (cleaned,),
        ).fetchone()
        if row is None:
            return False
        history_ref = row["history_ref"]
        connection.execute(
            "DELETE FROM run_history WHERE history_ref = ?",
            (history_ref,),
        )
        connection.execute("DELETE FROM runs WHERE run_id = ?", (cleaned,))
        connection.commit()
    return True


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


def last_transition_timestamp(history_ref: str) -> str | None:
    """Return the timestamp on the newest history entry, if any."""
    with _managed_connection() as connection:
        row = connection.execute(
            """
            SELECT transition_json
            FROM run_history
            WHERE history_ref = ?
            ORDER BY sequence DESC
            LIMIT 1
            """,
            (history_ref,),
        ).fetchone()
    if row is None:
        return None
    timestamp = str(json.loads(row["transition_json"]).get("timestamp") or "").strip()
    return timestamp or None


def backdate_last_transition(history_ref: str, timestamp: str) -> None:
    """Rewrite the newest history entry timestamp (test fixtures only)."""
    cleaned = str(timestamp or "").strip()
    if not cleaned:
        return
    with _managed_connection() as connection:
        row = connection.execute(
            """
            SELECT sequence, transition_json
            FROM run_history
            WHERE history_ref = ?
            ORDER BY sequence DESC
            LIMIT 1
            """,
            (history_ref,),
        ).fetchone()
        if row is None:
            return
        payload = json.loads(row["transition_json"])
        payload["timestamp"] = cleaned
        connection.execute(
            """
            UPDATE run_history
            SET transition_json = ?
            WHERE history_ref = ? AND sequence = ?
            """,
            (
                json.dumps(payload, separators=(",", ":"), sort_keys=True),
                history_ref,
                row["sequence"],
            ),
        )
        connection.commit()
