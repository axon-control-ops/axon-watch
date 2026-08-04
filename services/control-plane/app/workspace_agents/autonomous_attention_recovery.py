"""Reconcile stale attention approvals after a worker has recovered."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.persistence.autonomous_attention_decisions import supersede_pending_decision
from app.workspace_agents.run_outcome import latest_role_run_outcome


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
