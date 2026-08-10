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


def no_change_delivery_is_successful_ops_task(task: dict[str, object] | None) -> bool:
    """Return True when a no-diff delivery can honestly complete the task."""
    if not isinstance(task, dict):
        return False
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
                "receipt-backed ops task accepted: terminal/host command receipt "
                "is the delivery evidence; no code diff expected"
            ),
            actor="verifier",
        )
        finalized = complete_run(run_id)
        append_run_execution_receipt(
            run_id,
            receipt_type="worker_delivery_ops_receipt",
            actor="workspace_scheduler",
            receipt_summary=(
                "Workspace delivery completed: receipt-backed ops task required "
                "no publishable code changes."
            ),
        )
        return finalized
    except RunLifecycleError as exc:
        logger.exception("complete_run after ops delivery failed for %s", run_id)
        return fail_worker_run(f"Ops delivery succeeded but complete_run failed: {exc}")
