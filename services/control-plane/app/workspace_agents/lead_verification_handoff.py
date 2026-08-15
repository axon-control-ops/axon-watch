"""Route specialist verification handoffs to the owning role before Lead synthesis."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.persistence import task_store
from app.workspace_agents.lead_text import truncate_text
from app.workspace_agents.verification_execution import (
    build_verification_acceptance_evaluation,
    complete_verification_no_change_delivery,
    extract_verification_commands,
    is_verification_task,
    resolve_verification_baseline,
    source_run_from_verification_goal,
    verification_approved_command_prefixes,
    verification_commands_for_task,
    verification_terminal_jobs_for_run,
    verification_worker_prompt_clause,
)

logger = logging.getLogger(__name__)

_RUNTIME_BLOCKED_RE = re.compile(
    r"\b("
    r"blocked in this (?:headless )?runtime|"
    r"could not execute|"
    r"no approved shell|"
    r"scoped terminal job|"
    r"axon-agent-terminal-job|"
    r"headless runtime"
    r")\b",
    re.IGNORECASE,
)
_VERIFY_INTENT_RE = re.compile(
    r"\b("
    r"npm test|npx tsx|npx jest|"
    r"read-only verify|verify script|"
    r"run (?:the )?test|attach stdout"
    r")\b",
    re.IGNORECASE,
)


def looks_like_verification_handoff(
    *,
    blockers: str = "",
    lead_next: str = "",
    reply_text: str | None = None,
) -> bool:
    """True when a specialist finished code but could not run verify commands in-worker."""
    blob = " ".join(
        part.strip()
        for part in (blockers, lead_next, reply_text or "")
        if part and part.strip()
    )
    if not blob:
        return False
    if not _VERIFY_INTENT_RE.search(blob):
        return False
    return _RUNTIME_BLOCKED_RE.search(blob) is not None


def _verification_goal(
    *,
    employee_name: str,
    employee_role: str,
    run_id: str,
    commands: list[str],
) -> str:
    name = (employee_name or employee_role or "specialist").strip()
    role = (employee_role or "specialist").strip()
    command_hint = (
        "; ".join(f"`{command}`" for command in commands[:3])
        if commands
        else "`npm test` and read-only verify script"
    )
    return truncate_text(
        f"Verification after {name} ({role}): run scoped verify commands and attach stdout "
        f"receipts — {command_hint} [from run {run_id}]",
        max_len=420,
    )


def enqueue_specialist_verification_task(
    *,
    workspace_id: str,
    employee_name: str,
    employee_role: str,
    run_id: str,
    reply_text: str | None = None,
    blockers: str = "",
) -> dict[str, Any] | None:
    """Create an open specialist-owned verification task (tests/verify only)."""
    workspace = workspace_id.strip()
    role = str(employee_role or "").strip().lower()
    cleaned_run = str(run_id or "").strip()
    if not workspace or not role or not cleaned_run:
        return None
    if role in {"lead", "watcher", "overview_agent"}:
        return None

    for status in ("open", "leased"):
        for row in task_store.list_tasks(workspace_id=workspace, status=status, limit=100):
            if str(row.get("owner_role") or "").strip().lower() != role:
                continue
            goal = str(row.get("goal") or "")
            if cleaned_run in goal and goal.lower().startswith("verification after"):
                return row

    commands = extract_verification_commands(reply_text)
    goal_text = _verification_goal(
        employee_name=employee_name,
        employee_role=role,
        run_id=cleaned_run,
        commands=commands,
    )
    acceptance = (
        "Run the verify commands via axon-agent-terminal-job or an approved wrapper on a "
        "scoped task. Attach stdout/stderr receipts. Prefer read-only verify before any "
        "APPLY=true writes. Minimal in-scope fixes only if a test proves a defect. "
        "End with Confidence: N/10."
    )
    if blockers.strip():
        acceptance = f"{acceptance} Blockers from prior shift: {truncate_text(blockers, max_len=180)}"

    try:
        return task_store.create_task(
            workspace_id=workspace,
            goal=goal_text,
            acceptance_criteria=acceptance,
            risk="normal",
            owner_role=role,
            attempt_budget=2,
            allowed_paths=["tests", "services", "services/ops"],
        )
    except task_store.TaskLedgerError as exc:
        logger.warning("specialist verification task create failed: %s", exc)
        return None


def find_open_verification_task(
    workspace_id: str,
    owner_role: str,
) -> dict[str, Any] | None:
    """Newest open verification ticket for a specialist role, if any."""
    workspace = str(workspace_id or "").strip()
    role = str(owner_role or "").strip().lower()
    if not workspace or not role or role in {"lead", "watcher", "overview_agent"}:
        return None
    candidates: list[dict[str, Any]] = []
    for status in ("open", "leased"):
        for row in task_store.list_tasks(workspace_id=workspace, status=status, limit=100):
            if str(row.get("owner_role") or "").strip().lower() != role:
                continue
            goal = str(row.get("goal") or "")
            if goal.lower().startswith("verification after"):
                candidates.append(row)
    if not candidates:
        return None
    candidates.sort(key=lambda row: str(row.get("updated_at") or ""), reverse=True)
    return candidates[0]


def try_lease_open_verification_task(
    *,
    workspace_id: str,
    owner_role: str,
    lease_holder: str,
    run_id: str | None = None,
) -> dict[str, Any] | None:
    """Lease the newest open verification ticket so Lane B / terminal jobs get scope."""
    task = find_open_verification_task(workspace_id, owner_role)
    if task is None:
        return None
    status = str(task.get("status") or "").strip().lower()
    task_id = str(task.get("task_id") or "").strip()
    if not task_id:
        return None
    if status == "leased":
        return task
    if status != "open":
        return None
    try:
        return task_store.lease_task(
            task_id,
            lease_holder=lease_holder,
            run_id=run_id,
        )
    except task_store.TaskLedgerError as exc:
        logger.info("verification task lease skipped for %s: %s", task_id, exc)
        return None


__all__ = [
    "build_verification_acceptance_evaluation",
    "complete_verification_no_change_delivery",
    "enqueue_specialist_verification_task",
    "extract_verification_commands",
    "find_open_verification_task",
    "is_verification_task",
    "looks_like_verification_handoff",
    "try_lease_open_verification_task",
    "verification_approved_command_prefixes",
    "resolve_verification_baseline",
    "source_run_from_verification_goal",
    "verification_commands_for_task",
    "verification_worker_prompt_clause",
]
