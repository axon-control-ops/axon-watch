"""Small state and setup helpers for continuous worker dispatch."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from app.runs.service import (
    RunLifecycleError,
    RunNotFoundError,
    append_run_execution_receipt,
    fail_run,
)
from app.persistence import task_store
from app.workspace_agents.verification_execution import (
    is_verification_task,
    resolve_verification_baseline,
    verification_commands_for_task,
)
from app.workspace_agents.worker_isolation import (
    cleanup_worker_isolation,
    create_worker_isolation,
)

logger = logging.getLogger(__name__)

_active_run_ids: set[str] = set()
_active_run_ids_lock = threading.Lock()


def claim_worker_dispatch(run_id: str) -> bool:
    with _active_run_ids_lock:
        if run_id in _active_run_ids:
            return False
        _active_run_ids.add(run_id)
        return True


def release_worker_dispatch(run_id: str) -> None:
    with _active_run_ids_lock:
        _active_run_ids.discard(run_id)


def fail_worker_run(run_id: str, *, receipt_summary: str) -> dict[str, Any] | None:
    try:
        return fail_run(
            run_id,
            receipt_summary=receipt_summary,
            actor="workspace_scheduler",
        )
    except (RunLifecycleError, RunNotFoundError):
        logger.exception("continuous worker fail_run unavailable for %s", run_id)
        return None


def finalize_failed_worker_task(
    *,
    workspace_id: str,
    task_id: str,
    run_id: str,
    employee_role: str,
    employee_name: str,
    error: str,
) -> None:
    try:
        task_store.fail_task(task_id, run_id=run_id)
    except task_store.TaskLedgerError:
        logger.exception("task fail after dispatch error for %s", task_id)
    try:
        from app.workspace_agents.lead_replan import notify_lead_after_worker_task

        notify_lead_after_worker_task(
            workspace_id=workspace_id,
            task_id=task_id,
            run_id=run_id,
            employee_role=employee_role,
            employee_name=employee_name,
            phase="failed",
            reply_text=error,
        )
    except Exception:  # noqa: BLE001
        logger.exception("lead notify after dispatch error for %s", run_id)


def cleanup_dispatch_isolation(run_id: str, isolation_root: Path) -> None:
    cleanup = cleanup_worker_isolation(isolation_root)
    try:
        append_run_execution_receipt(
            run_id,
            receipt_type="worker_isolation_cleanup",
            receipt_summary=(
                f"worker isolation cleanup removed={cleanup.get('removed')} "
                f"cleaned={cleanup.get('cleaned')}"
            ),
            actor="workspace_scheduler",
            success=bool(cleanup.get("cleaned")),
            intent="worker_isolation",
        )
    except (RunLifecycleError, RunNotFoundError):
        logger.exception("worker isolation cleanup receipt failed for %s", run_id)


def create_dispatch_isolation(
    *, workspace_id: str, run_id: str, task: dict[str, Any]
) -> Path:
    baseline_commit = None
    baseline_ref = None
    if is_verification_task(task):
        baseline_commit, baseline_ref = resolve_verification_baseline(
            workspace_id=workspace_id,
            task=task,
        )
    return create_worker_isolation(
        workspace_id=workspace_id,
        run_id=run_id,
        baseline_commit=baseline_commit,
        baseline_ref=baseline_ref,
    )


def enqueue_verification_terminal_jobs(
    *, workspace_id: str, run_id: str, task: dict[str, Any]
) -> None:
    """Start bounded verification jobs before the worker reviews their output."""
    if not is_verification_task(task):
        return
    commands = verification_commands_for_task(task)
    if not commands:
        logger.info("verification shift %s has no extracted verify commands", run_id)
        return

    from app.terminal.agent_jobs import enqueue_agent_terminal_job

    for command in commands[:3]:
        try:
            enqueue_agent_terminal_job(
                workspace_id=workspace_id,
                command=command,
                run_id=run_id,
                stream_to_chat=True,
                source_workspace_id=workspace_id,
            )
            append_run_execution_receipt(
                run_id,
                receipt_type="verification_terminal_enqueued",
                receipt_summary=f"Auto-enqueued verify command: {command[:140]}",
                actor="workspace_scheduler",
                success=True,
                intent="verification_terminal",
            )
        except Exception as exc:  # noqa: BLE001 - record one command and continue
            logger.warning(
                "verification terminal enqueue failed run=%s command=%s: %s",
                run_id,
                command[:80],
                exc,
            )
            append_run_execution_receipt(
                run_id,
                receipt_type="verification_terminal_enqueue_failed",
                receipt_summary=f"Verify enqueue failed for `{command[:80]}`: {exc}",
                actor="workspace_scheduler",
                success=False,
                intent="verification_terminal",
            )


__all__ = [
    "claim_worker_dispatch",
    "cleanup_dispatch_isolation",
    "create_dispatch_isolation",
    "enqueue_verification_terminal_jobs",
    "fail_worker_run",
    "finalize_failed_worker_task",
    "release_worker_dispatch",
]
