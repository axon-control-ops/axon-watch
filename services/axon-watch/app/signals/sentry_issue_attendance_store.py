"""Persist operator attend/suppress receipts for production Sentry issues."""

from __future__ import annotations

from contextlib import contextmanager
import os
from typing import Any

from app.persistence import watch_store_sqlite
from app.signals.iso_time import utc_now_iso


@contextmanager
def _managed_connection():
    connection = watch_store_sqlite.connect(os.environ.get("AXON_WATCH_WATCH_SERVICE_DB"))
    try:
        ensure_sentry_attend_schema(connection)
        yield connection
    finally:
        connection.close()


def ensure_sentry_attend_schema(connection: Any) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS watch_sentry_issue_attendances (
            issue_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            confirm_release TEXT NOT NULL,
            attended_at TEXT NOT NULL,
            attended_by TEXT NOT NULL,
            mode TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_watch_sentry_issue_attendances_workspace
            ON watch_sentry_issue_attendances(workspace_id, attended_at DESC);
        """
    )
    connection.commit()


def reset_store() -> None:
    with _managed_connection() as connection:
        connection.execute("DELETE FROM watch_sentry_issue_attendances")
        connection.commit()


def attend_issue(
    *,
    issue_id: str,
    workspace_id: str,
    confirm_release: str,
    attended_by: str = "operator",
    mode: str = "mute_until_newer_release",
) -> dict[str, object]:
    cleaned_issue = str(issue_id or "").strip()
    cleaned_workspace = str(workspace_id or "").strip() or "workspace_dashpro"
    cleaned_release = str(confirm_release or "").strip() or "attended"
    cleaned_by = str(attended_by or "operator").strip() or "operator"
    cleaned_mode = str(mode or "mute_until_newer_release").strip() or "mute_until_newer_release"
    if not cleaned_issue:
        raise ValueError("issue_id is required")
    attended_at = utc_now_iso()
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO watch_sentry_issue_attendances (
                issue_id, workspace_id, confirm_release, attended_at, attended_by, mode
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(issue_id) DO UPDATE SET
                workspace_id = excluded.workspace_id,
                confirm_release = excluded.confirm_release,
                attended_at = excluded.attended_at,
                attended_by = excluded.attended_by,
                mode = excluded.mode
            """,
            (
                cleaned_issue,
                cleaned_workspace,
                cleaned_release,
                attended_at,
                cleaned_by,
                cleaned_mode,
            ),
        )
        connection.commit()
    return {
        "issue_id": cleaned_issue,
        "workspace_id": cleaned_workspace,
        "confirm_release": cleaned_release,
        "attended_at": attended_at,
        "attended_by": cleaned_by,
        "mode": cleaned_mode,
    }


def list_attendances(*, workspace_id: str | None = None) -> list[dict[str, object]]:
    scoped = str(workspace_id or "").strip()
    with _managed_connection() as connection:
        if scoped:
            rows = connection.execute(
                """
                SELECT issue_id, workspace_id, confirm_release, attended_at, attended_by, mode
                FROM watch_sentry_issue_attendances
                WHERE workspace_id = ?
                ORDER BY attended_at DESC
                """,
                (scoped,),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT issue_id, workspace_id, confirm_release, attended_at, attended_by, mode
                FROM watch_sentry_issue_attendances
                ORDER BY attended_at DESC
                """
            ).fetchall()
    return [
        {
            "issue_id": str(row["issue_id"]),
            "workspace_id": str(row["workspace_id"]),
            "confirm_release": str(row["confirm_release"]),
            "attended_at": str(row["attended_at"]),
            "attended_by": str(row["attended_by"]),
            "mode": str(row["mode"]),
        }
        for row in rows
    ]


def attendance_map(*, workspace_id: str | None = None) -> dict[str, dict[str, object]]:
    return {str(item["issue_id"]): item for item in list_attendances(workspace_id=workspace_id)}


def clear_attendance(issue_id: str) -> bool:
    cleaned = str(issue_id or "").strip()
    if not cleaned:
        return False
    with _managed_connection() as connection:
        connection.execute(
            "DELETE FROM watch_sentry_issue_attendances WHERE issue_id = ?",
            (cleaned,),
        )
        changed = connection.total_changes > 0
        connection.commit()
    return changed


def should_suppress_issue(
    issue: dict[str, object],
    attendance: dict[str, object] | None,
) -> bool:
    """Suppress production issues attended after OTA/build until a newer release appears."""
    if not attendance:
        return False
    mode = str(attendance.get("mode") or "").strip()
    if mode not in {"mute_until_newer_release", "attended"}:
        return False
    confirm_release = str(attendance.get("confirm_release") or "").strip()
    if not confirm_release:
        return True
    last_release = str(issue.get("last_release") or issue.get("first_release") or "").strip()
    if not last_release:
        # No release metadata on the issue — keep suppressed after attend.
        return True
    if last_release == confirm_release:
        return True
    # Heuristic: if Sentry reports the same or older release string, stay muted.
    # Newer release strings typically differ (build number / OTA id).
    return False


__all__ = [
    "attend_issue",
    "attendance_map",
    "clear_attendance",
    "ensure_sentry_attend_schema",
    "list_attendances",
    "reset_store",
    "should_suppress_issue",
]
