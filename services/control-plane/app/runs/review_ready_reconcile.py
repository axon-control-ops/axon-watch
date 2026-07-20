"""Complete abandoned operator review_ready checkpoints so briefing stays honest."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import run_store

logger = logging.getLogger(__name__)

# Long enough for same-session review; short enough to clear overnight clutter.
DEFAULT_REVIEW_READY_STALE_SECONDS = 14400.0
_ABANDON_SUMMARY = "Abandoned review_ready auto-completed after idle timeout"


def review_ready_stale_seconds() -> float:
    raw = os.environ.get("AXON_WATCH_REVIEW_READY_STALE_SECONDS", "").strip()
    if not raw:
        return DEFAULT_REVIEW_READY_STALE_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_REVIEW_READY_STALE_SECONDS
    return max(60.0, value)


def _parse_iso(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _review_ready_age_seconds(record: dict[str, Any], *, now: datetime) -> float | None:
    """Age since the run entered (or last touched) review_ready."""
    stamp = _parse_iso(record.get("updated_at")) or _parse_iso(record.get("started_at"))
    if stamp is None:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return max(0.0, (now - stamp).total_seconds())


def reap_abandoned_review_ready_runs(
    *,
    now: datetime | None = None,
    stale_seconds: float | None = None,
) -> list[str]:
    """Complete idle untagged review_ready runs older than the wall-clock TTL.

    Role-tagged worker shifts are left alone (employee stale reaper owns those).
    Approval waits are never auto-completed. Fresh review checkpoints stay until
    the operator completes or resumes them.
    """
    from app.runs.service import RunLifecycleError, RunNotFoundError, _transition_record

    cutoff = (
        review_ready_stale_seconds()
        if stale_seconds is None
        else max(60.0, float(stale_seconds))
    )
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)

    completed: list[str] = []
    for record in run_store.list_runs():
        if str(record.get("employee_role") or "").strip():
            continue
        phase = str(record.get("phase") or "").strip()
        if phase != "review_ready" or is_terminal_phase(phase):
            continue
        age = _review_ready_age_seconds(record, now=moment)
        if age is None or age < cutoff:
            continue
        run_id = str(record.get("run_id") or "").strip()
        if not run_id:
            continue
        receipt_summary = f"{_ABANDON_SUMMARY} ({int(age)}s > {int(cutoff)}s)"
        try:
            _transition_record(
                record,
                to_phase="completed",
                current_step="Run completed",
                actor="control-plane",
                receipt_type="review_ready_abandon",
                receipt_summary=receipt_summary,
            )
        except (RunLifecycleError, RunNotFoundError):
            logger.exception("abandoned review_ready complete skipped for %s", run_id)
            continue
        completed.append(run_id)
        logger.info(
            "completed abandoned review_ready run %s idle_s=%.0f",
            run_id,
            age,
        )
    return completed


__all__ = [
    "DEFAULT_REVIEW_READY_STALE_SECONDS",
    "reap_abandoned_review_ready_runs",
    "review_ready_stale_seconds",
]
