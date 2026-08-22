"""Provenance-bearing recovery lessons. Unverified lessons are never policy."""

from __future__ import annotations

import uuid
from typing import Any

from app.platform_recovery.classifier import redact_secrets
from app.platform_recovery.states import normalize_failure_class
from app.platform_recovery.store import managed_connection, utc_now_iso


def record_lesson(
    *,
    failure_class: str,
    root_cause: str,
    recovery: str,
    verification: str,
    confidence: str = "low",
    provenance_run_id: str = "",
    verified: bool = False,
) -> dict[str, Any]:
    lesson_id = f"lesson_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    payload = {
        "lesson_id": lesson_id,
        "failure_class": normalize_failure_class(failure_class),
        "root_cause": redact_secrets(root_cause),
        "recovery": redact_secrets(recovery),
        "verification": redact_secrets(verification),
        "confidence": str(confidence or "low"),
        "provenance_run_id": str(provenance_run_id or ""),
        "verified": bool(verified),
        "created_at": now,
        "policy_adopted": False,
    }
    with managed_connection() as conn:
        conn.execute(
            """
            INSERT INTO recovery_lessons (
                lesson_id, failure_class, root_cause, recovery, verification,
                confidence, provenance_run_id, verified, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["lesson_id"],
                payload["failure_class"],
                payload["root_cause"],
                payload["recovery"],
                payload["verification"],
                payload["confidence"],
                payload["provenance_run_id"],
                1 if payload["verified"] else 0,
                now,
            ),
        )
        conn.commit()
    return payload


def list_lessons(*, failure_class: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM recovery_lessons"
    params: tuple[str, ...] = ()
    if failure_class:
        sql += " WHERE failure_class = ?"
        params = (normalize_failure_class(failure_class),)
    sql += " ORDER BY created_at DESC"
    with managed_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [
        {
            "lesson_id": row["lesson_id"],
            "failure_class": row["failure_class"],
            "root_cause": row["root_cause"],
            "recovery": row["recovery"],
            "verification": row["verification"],
            "confidence": row["confidence"],
            "provenance_run_id": row["provenance_run_id"],
            "verified": bool(row["verified"]),
            "created_at": row["created_at"],
            "policy_adopted": False,
        }
        for row in rows
    ]
