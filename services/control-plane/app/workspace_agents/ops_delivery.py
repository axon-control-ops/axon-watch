"""Helpers for receipt-backed workspace ops deliveries."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from app.runs.service import RunLifecycleError, append_run_execution_receipt, complete_run

logger = logging.getLogger(__name__)

_OPS_COMMAND_PATTERNS = (
    "axon-agent-terminal-job",
    "npm run ota",
    "eas update",
    "expo update",
    "supabase db push",
    "gh workflow run",
)

_LEAD_COORDINATION_MARKERS = (
    "lead: advance",
    "toward done",
    "sole truth",
    "lead plan",
    "plan ",
)

_LEAD_COORDINATION_ACTIONS = (
    "assign",
    "decide",
    "decision",
    "escalate",
    "report",
    "brief",
    "rollup",
    "verify",
    "receipt",
)


def _no_change_lead_coordination_is_successful(task: dict[str, object]) -> bool:
    """True for Lead coordination tasks whose output is a decision/receipt, not a diff."""
    owner_role = str(task.get("owner_role") or "").strip().lower()
    if owner_role != "lead":
        return False
    blob = " ".join(
        str(task.get(key) or "")
        for key in ("goal", "acceptance_criteria", "terminal_outcome")
    ).lower()
    if not blob:
        return False
    has_plan_context = any(marker in blob for marker in _LEAD_COORDINATION_MARKERS)
    has_coordination_action = any(action in blob for action in _LEAD_COORDINATION_ACTIONS)
    return has_plan_context and has_coordination_action


def no_change_delivery_is_successful_ops_task(task: dict[str, object] | None) -> bool:
    """Return True when a no-diff delivery can honestly complete the task."""
    if not isinstance(task, dict):
        return False
    if _no_change_lead_coordination_is_successful(task):
        return True
    blob = " ".join(
        str(task.get(key) or "")
        for key in ("goal", "acceptance_criteria", "terminal_outcome")
    ).lower()
    if not blob or not any(pattern in blob for pattern in _OPS_COMMAND_PATTERNS):
        return False
    return any(
        marker in blob
        for marker in (
            "receipt",
            "run the command",
            "ops command",
            "ota",
            "publish",
            "migration",
            "workflow",
            "supabase",
        )
    )


def complete_ops_no_change_delivery(
    run_id: str,
    *,
    fail_worker_run: Callable[[str], dict[str, Any] | None],
) -> dict[str, Any] | None:
    """Complete a receipt-backed ops task whose delivery has no git diff."""
    try:
        from app.workspace_agents.verifier_contract import record_acceptance_evidence

        record_acceptance_evidence(
            run_id,
            passed=True,
            summary=(
                "receipt-backed ops/coordination task accepted: terminal, host, "
                "or Lead decision receipt is the delivery evidence; no code diff expected"
            ),
            actor="verifier",
        )
        finalized = complete_run(run_id)
        append_run_execution_receipt(
            run_id,
            receipt_type="worker_delivery_ops_receipt",
            actor="workspace_scheduler",
            receipt_summary=(
                "Workspace delivery completed: receipt-backed ops/coordination task "
                "required no publishable code changes."
            ),
        )
        return finalized
    except RunLifecycleError as exc:
        logger.exception("complete_run after ops delivery failed for %s", run_id)
        return fail_worker_run(f"Ops delivery succeeded but complete_run failed: {exc}")
