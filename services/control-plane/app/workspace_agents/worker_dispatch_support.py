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
    resolve_verification_command,
    select_verification_commands,
    verification_commands_for_task,
)
from app.workspace_agents.worker_isolation import (
    cleanup_worker_isolation,
    create_worker_isolation,
)

logger = logging.getLogger(__name__)

_active_run_ids: set[str] = set()
_active_run_ids_lock = threading.Lock()
_active_task_ids: dict[str, str] = {}
# Runs whose cwd is the durable composer Sandbox — must not be torn down as worker isolation.
_sandbox_borrowed_run_ids: set[str] = set()


def claim_worker_dispatch(run_id: str, task_id: str = "") -> bool:
    from app.platform_recovery.dispatch_guard import DuplicateDispatchError, assert_dispatch_allowed

    with _active_run_ids_lock:
        try:
            assert_dispatch_allowed(
                task_id=task_id or None,
                run_id=run_id,
                active_run_ids=_active_run_ids,
                active_task_ids=_active_task_ids,
            )
        except DuplicateDispatchError:
            return False
        if run_id in _active_run_ids:
            return False
        _active_run_ids.add(run_id)
        cleaned_task = str(task_id or "").strip()
        if cleaned_task:
            _active_task_ids[cleaned_task] = run_id
        return True


def release_worker_dispatch(run_id: str) -> None:
    with _active_run_ids_lock:
        _active_run_ids.discard(run_id)
        stale = [task_id for task_id, owner in _active_task_ids.items() if owner == run_id]
        for task_id in stale:
            _active_task_ids.pop(task_id, None)


def is_worker_dispatch_active(run_id: str) -> bool:
    """True when a dispatch thread already claimed this run in-memory.

    Lets the stale reaper tell "no thread ever started" apart from "a thread
    is alive and mid-startup" before it decides a run never got dispatched.
    """
    with _active_run_ids_lock:
        return run_id in _active_run_ids


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
    cleaned_run = str(run_id or "").strip()
    with _active_run_ids_lock:
        borrowed = cleaned_run in _sandbox_borrowed_run_ids
        if borrowed:
            _sandbox_borrowed_run_ids.discard(cleaned_run)
    if borrowed:
        return
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


def _composer_sandbox_checkout(workspace_id: str) -> Path | None:
    """Return the durable Sandbox checkout when enabled and materialized."""
    try:
        from app.cli_runtime.composer_sandbox import (
            resolve_sandbox_workspace_root,
            sandbox_status,
        )

        status = sandbox_status(workspace_id)
        if not status.get("enabled") or not status.get("materialized"):
            return None
        return resolve_sandbox_workspace_root(workspace_id)
    except Exception:  # noqa: BLE001 — verification dispatch must fall back to isolation
        logger.exception("composer Sandbox checkout resolve failed for %s", workspace_id)
        return None


def create_dispatch_isolation(
    *, workspace_id: str, run_id: str, task: dict[str, Any]
) -> Path:
    cleaned_run = str(run_id or "").strip()
    if is_verification_task(task):
        sandbox_root = _composer_sandbox_checkout(workspace_id)
        if sandbox_root is not None:
            with _active_run_ids_lock:
                _sandbox_borrowed_run_ids.add(cleaned_run)
            return sandbox_root

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


def _verification_command_root(workspace_id: str) -> Path | None:
    """Root the verify commands actually run against (the agent PTY cwd)."""
    sandbox_root = _composer_sandbox_checkout(workspace_id)
    if sandbox_root is not None:
        return sandbox_root
    from app.terminal.workspace_roots import resolve_workspace_root

    try:
        return Path(resolve_workspace_root(workspace_id))
    except Exception:  # noqa: BLE001 - preflight is best effort
        return None


def enqueue_verification_terminal_jobs(
    *, workspace_id: str, run_id: str, task: dict[str, Any]
) -> None:
    """Start bounded verification jobs before the worker reviews their output."""
    if not is_verification_task(task):
        return
    commands = verification_commands_for_task(task)
    commands = select_verification_commands(commands, limit=3)
    if not commands:
        logger.info("verification shift %s has no extracted verify commands", run_id)
        return

    from app.terminal.agent_jobs import TARGET_SANDBOX, TARGET_WORKSPACE, enqueue_agent_terminal_job

    workspace_root = _verification_command_root(workspace_id)
    job_target = TARGET_WORKSPACE
    try:
        from app.cli_runtime.composer_sandbox import sandbox_status

        status = sandbox_status(workspace_id)
        if status.get("enabled") and status.get("materialized"):
            job_target = TARGET_SANDBOX
    except Exception:  # noqa: BLE001 — fall back to bound root
        pass
    for command in commands:
        runnable, note = resolve_verification_command(command, workspace_root)
        if runnable is None:
            # Running a command against a path that does not exist only burns a
            # run and reports "test path absent". Say so up front instead.
            logger.info("verification command skipped run=%s: %s", run_id, note)
            append_run_execution_receipt(
                run_id,
                receipt_type="verification_terminal_unrunnable",
                receipt_summary=f"Skipped verify command `{command[:100]}`: {note}",
                actor="workspace_scheduler",
                success=False,
                intent="verification_terminal",
            )
            continue
        try:
            enqueue_agent_terminal_job(
                workspace_id=workspace_id,
                command=runnable,
                run_id=run_id,
                stream_to_chat=True,
                source_workspace_id=workspace_id,
                target=job_target,
            )
            append_run_execution_receipt(
                run_id,
                receipt_type="verification_terminal_enqueued",
                receipt_summary=(
                    f"Auto-enqueued verify command: {runnable[:140]}"
                    + (f" ({note})" if note else "")
                ),
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
    "is_worker_dispatch_active",
    "release_worker_dispatch",
]
