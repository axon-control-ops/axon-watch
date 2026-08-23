"""Retry fingerprint persistence helpers."""

from __future__ import annotations

from app.platform_recovery.retry_fingerprint import RetryDecision, decide_retry
from app.platform_recovery.store import managed_connection, utc_now_iso


def record_retry_attempt(fingerprint: str, *, max_attempts: int) -> RetryDecision:
    cleaned = str(fingerprint or "").strip()
    prior = 0
    with managed_connection() as conn:
        row = conn.execute(
            "SELECT attempt_count FROM retry_fingerprints WHERE fingerprint = ?",
            (cleaned,),
        ).fetchone()
        if row is not None:
            prior = int(row["attempt_count"] or 0)
        decision = decide_retry(
            fingerprint=cleaned, prior_attempts=prior, max_attempts=max_attempts
        )
        conn.execute(
            """
            INSERT INTO retry_fingerprints (fingerprint, attempt_count, last_action, last_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(fingerprint) DO UPDATE SET
                attempt_count=excluded.attempt_count,
                last_action=excluded.last_action,
                last_at=excluded.last_at
            """,
            (cleaned, decision.attempt, decision.action, utc_now_iso()),
        )
        conn.commit()
    return decision
