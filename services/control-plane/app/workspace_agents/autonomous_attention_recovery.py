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


def _failed_shift_role(receipt: dict[str, Any], workspace_id: str) -> str | None:
    payload = receipt.get("payload") if isinstance(receipt.get("payload"), dict) else {}
    structured = str(payload.get("subject_role") or "").strip().lower()
    if structured:
        return structured
    workspace = str(workspace_id or "").strip()
    dedupe_key = str(receipt.get("dedupe_key") or "").strip()
    prefix = f"failed_shift:{workspace}:"
    if not workspace or not dedupe_key.startswith(prefix):
        return None
    # lead_team_checkin.collect_failed_shift_findings intentionally keys this
    # "failed_shift:{workspace}:{role}" with no run_id — a soft, role-scoped
    # key so repeat failures of the same role never stack duplicate Needs-you
    # cards. There is nothing after the role to partition on.
    role = dedupe_key[len(prefix) :].strip().lower()
    return role or None


def _completion_is_newer_than_failure(
    receipt: dict[str, Any], outcome: dict[str, str]
) -> bool:
    """Do not clear a decision unless completion post-dates its source failure."""
    payload = receipt.get("payload") if isinstance(receipt.get("payload"), dict) else {}
    subject_run_id = str(payload.get("subject_run_id") or "").strip()
    completed_run_id = str(outcome.get("run_id") or "").strip()
    if not subject_run_id:
        return bool(completed_run_id)
    if not completed_run_id or completed_run_id == subject_run_id:
        return False
    try:
        from app.persistence import run_store

        failed = run_store.get_run(subject_run_id)
        completed = run_store.get_run(completed_run_id)
    except Exception:
        return False
    if not isinstance(failed, dict) or not isinstance(completed, dict):
        return False
    failed_stamp = str(
        failed.get("ended_at") or failed.get("updated_at") or failed.get("started_at") or ""
    )
    completed_stamp = str(
        completed.get("ended_at")
        or completed.get("updated_at")
        or completed.get("started_at")
        or ""
    )
    return bool(failed_stamp and completed_stamp and completed_stamp > failed_stamp)


def reconcile_recovered_failed_shift_decisions(
    workspace_id: str,
    pending: list[dict[str, Any]],
    *,
    latest_outcome: Callable[[str, str], dict[str, str] | None] = latest_role_run_outcome,
) -> None:
    """Close only failed-shift approvals superseded by later successful work."""
    outcomes: dict[str, dict[str, str] | None] = {}
    for receipt in pending:
        role = _failed_shift_role(receipt, workspace_id)
        if role is None:
            continue
        outcomes.setdefault(role, latest_outcome(workspace_id, role))
        outcome = outcomes[role] or {}
        # A completed latest run only supersedes the alert when it is distinct
        # from and newer than the exact source failure recorded in the payload.
        if (
            str(outcome.get("outcome") or "").strip().lower() == "completed"
            and _completion_is_newer_than_failure(receipt, outcome)
        ):
            supersede_pending_decision(str(receipt.get("receipt_id") or ""))


def reconcile_workspace_recovered_decisions(
    workspace_id: str,
    *,
    completed_run: dict[str, Any] | None = None,
) -> None:
    """Immediately remove failed-shift decisions made obsolete by recovery."""
    from app.persistence import autonomous_attention_store
    from app.persistence.autonomous_attention_decisions import supersede_pending_decision

    workspace = str(workspace_id or "").strip()
    if not workspace:
        return
    pending = autonomous_attention_store.list_pending_decisions(
        limit=500,
        workspace_id=workspace,
    )
    # At the completion event we know causality even when SQLite timestamps
    # share one-second precision: this distinct run completed after the pending
    # decision already existed.
    if isinstance(completed_run, dict):
        completed_role = str(completed_run.get("employee_role") or "").strip().lower()
        completed_id = str(completed_run.get("run_id") or "").strip()
        if completed_role and completed_id:
            for receipt in pending:
                if _failed_shift_role(receipt, workspace) != completed_role:
                    continue
                payload = (
                    receipt.get("payload")
                    if isinstance(receipt.get("payload"), dict)
                    else {}
                )
                source_id = str(payload.get("subject_run_id") or "").strip()
                if source_id and source_id == completed_id:
                    continue
                supersede_pending_decision(str(receipt.get("receipt_id") or ""))
            pending = autonomous_attention_store.list_pending_decisions(
                limit=500,
                workspace_id=workspace,
            )
    reconcile_recovered_failed_shift_decisions(workspace, pending)


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
