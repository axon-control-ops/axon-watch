"""Reconcile stale attention approvals after a worker has recovered."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from app.persistence.autonomous_attention_decisions import (
    expire_stale_pending_decision,
    supersede_pending_decision,
)
from app.workspace_agents.run_outcome import latest_role_run_outcome

DEFAULT_STALE_MAX_AGE_HOURS = 24.0


def _parse_iso(raw: str | None) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _failed_shift_role(receipt: dict[str, Any], workspace_id: str) -> tuple[str, str] | None:
    workspace = str(workspace_id or "").strip()
    dedupe_key = str(receipt.get("dedupe_key") or "").strip()
    prefix = f"failed_shift:{workspace}:"
    if not workspace or not dedupe_key.startswith(prefix):
        return None
    role, separator, failed_run_id = dedupe_key[len(prefix) :].partition(":")
    role, failed_run_id = role.strip().lower(), failed_run_id.strip()
    return (role, failed_run_id) if separator and role and failed_run_id else None


def reconcile_recovered_failed_shift_decisions(
    workspace_id: str,
    pending: list[dict[str, Any]],
    *,
    latest_outcome: Callable[[str, str], dict[str, str] | None] = latest_role_run_outcome,
) -> None:
    """Close only failed-shift approvals superseded by later successful work."""
    outcomes: dict[str, dict[str, str] | None] = {}
    for receipt in pending:
        parsed = _failed_shift_role(receipt, workspace_id)
        if parsed is None:
            continue
        role, failed_run_id = parsed
        outcomes.setdefault(role, latest_outcome(workspace_id, role))
        outcome = outcomes[role] or {}
        completed_run_id = str(outcome.get("run_id") or "").strip()
        if (
            str(outcome.get("outcome") or "").strip().lower() == "completed"
            and completed_run_id
            and completed_run_id != failed_run_id
        ):
            supersede_pending_decision(str(receipt.get("receipt_id") or ""))


def sweep_stale_attention_decisions(
    *,
    max_age_hours: float = DEFAULT_STALE_MAX_AGE_HOURS,
    now: datetime | None = None,
    list_pending: Callable[[], list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    """Auto-clear "Needs You" items that sat untouched past max_age_hours.

    Unlike reconcile_recovered_failed_shift_decisions (which needs a proven
    successful run), this is a conservative time-based fallback for kinds
    with no cheap re-probe available (critical_signal connector/monitor
    alerts, usage-limit/auth blocks that never got manually cleared). Only
    clears an item when its dedupe_key has NOT recurred more recently —
    a genuinely ongoing problem keeps producing fresh receipts and must
    stay visible; only a one-off that never happened again gets expired.
    """
    from app.persistence.autonomous_attention_store import (
        list_pending_decisions,
        soft_dedupe_key,
    )

    current = now or datetime.now(timezone.utc)
    cutoff = current - timedelta(hours=max(0.0, max_age_hours))
    pending = (list_pending or (lambda: list_pending_decisions(limit=500)))()

    parsed_created: dict[str, datetime] = {}
    for receipt in pending:
        receipt_id = str(receipt.get("receipt_id") or "")
        created = _parse_iso(str(receipt.get("created_at") or ""))
        if receipt_id and created is not None:
            parsed_created[receipt_id] = created

    expired: list[dict[str, Any]] = []
    for receipt in pending:
        receipt_id = str(receipt.get("receipt_id") or "")
        created = parsed_created.get(receipt_id)
        if created is None or created >= cutoff:
            continue
        soft_key = soft_dedupe_key(str(receipt.get("dedupe_key") or ""))
        newer_recurrence = bool(soft_key) and any(
            other_id != receipt_id
            and soft_dedupe_key(str(other.get("dedupe_key") or "")) == soft_key
            and parsed_created.get(other_id, created) > created
            for other_id, other in ((str(r.get("receipt_id") or ""), r) for r in pending)
        )
        if newer_recurrence:
            continue
        result = expire_stale_pending_decision(receipt_id)
        if result is not None:
            expired.append(result)
    return expired
