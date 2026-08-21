"""Capability-aware routing when terminal or sandbox policy blocks an agent.

When a specialist cannot run a command (no scoped task, shell operators denied,
live Supabase ops without network scope), route autonomously to a capable owner:
same-role scoped task for ops scripts, or integrations for ship/CI shells.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import uuid4

from app.persistence import chat_store, run_store, task_store
from app.workspace_agents.assignment_messages import assignment_card, assignment_card_title
from app.workspace_agents.lead_text import truncate_text
from app.workspace_agents.verification_execution import (
    extract_verification_commands,
    select_verification_commands,
)

logger = logging.getLogger(__name__)

_TERMINAL_BLOCKED_RE = re.compile(
    r"\b("
    r"shell command was blocked|"
    r"shell command blocked|"
    r"shell is heavily restricted|"
    r"a shell command was blocked|"
    r"sandbox policy denied|"
    r"shell operators.*not allowed|"
    r"agent terminal run has no scoped task|"
    r"no scoped task|"
    r"does not match an approved wrapper|"
    r"use an approved wrapper"
    r")\b",
    re.IGNORECASE,
)
_LIVE_OPS_RE = re.compile(
    r"\b("
    r"supabase|"
    r"service[_ -]?role|"
    r"auth\.admin|"
    r"services/ops/|"
    r"APPLY=true|"
    r"fix-.*-email|"
    r"reset-password|"
    r"listusers"
    r")\b",
    re.IGNORECASE,
)
_OPS_SCRIPT_RE = re.compile(
    r"services/ops/[A-Za-z0-9_./-]+\.(?:ts|tsx|mjs|js)",
    re.IGNORECASE,
)
_SHIP_COMMAND_HINT_RE = re.compile(
    r"\b(npm run ota:|npm run vercel-build|eas-wrapper|watch-fast-gate)\b",
    re.IGNORECASE,
)
_DOCUMENT_RE = re.compile(
    r"\b("
    r"pdf|"
    r"rfq|"
    r"workbook|"
    r"quotation|"
    r"submission|"
    r"letterhead|"
    r"fill-rfq|"
    r"pdftotext|"
    r"document pack|"
    r"official form"
    r")\b",
    re.IGNORECASE,
)
_DOCUMENT_ALLOWED_PATHS = [
    "docs",
    "output",
    "assets",
    "website",
    "website/documents",
    "scripts",
]

_ROLE_CAPABILITY_ORDER: dict[str, tuple[str, ...]] = {
    "live_ops_scoped": ("backend", "integrations", "lead"),
    "ship_shell_no_task": ("integrations", "lead"),
    "document_scope": ("frontend", "lead", "backend"),
    "terminal_scope": ("frontend", "backend", "integrations", "lead"),
}


def looks_like_terminal_capability_handoff(
    *,
    reply_text: str | None = None,
    blockers: str = "",
    goal_hint: str = "",
) -> bool:
    """True when runtime output shows terminal/sandbox blocks that need rerouting."""
    blob = " ".join(
        part.strip()
        for part in (blockers, goal_hint, reply_text or "")
        if part and part.strip()
    )
    if not blob:
        return False
    return _TERMINAL_BLOCKED_RE.search(blob) is not None


def _capability_kind(*, blob: str, command: str) -> str:
    combined = f"{blob} {command}".strip()
    if _DOCUMENT_RE.search(combined):
        return "document_scope"
    if _SHIP_COMMAND_HINT_RE.search(combined) and not _LIVE_OPS_RE.search(combined):
        return "ship_shell_no_task"
    if _LIVE_OPS_RE.search(combined) or _OPS_SCRIPT_RE.search(combined):
        return "live_ops_scoped"
    return "terminal_scope"


def _pick_target_role(*, source_role: str, capability: str) -> str:
    order = _ROLE_CAPABILITY_ORDER.get(capability, ("backend", "integrations", "lead"))
    normalized = str(source_role or "").strip().lower()
    if normalized in order:
        return normalized
    return order[0]


def _extract_goal_and_commands(
    *,
    reply_text: str | None,
    goal_hint: str,
    command: str,
) -> tuple[str, list[str]]:
    commands = select_verification_commands(
        extract_verification_commands(reply_text or "") or [],
        limit=3,
    )
    for candidate in (command, goal_hint):
        cleaned = " ".join(str(candidate or "").split()).strip()
        if cleaned and cleaned not in commands:
            normalized_cmds = select_verification_commands([cleaned], limit=1)
            for item in normalized_cmds:
                if item not in commands:
                    commands.append(item)
    for match in _OPS_SCRIPT_RE.finditer(f"{reply_text or ''} {goal_hint} {command}"):
        script = match.group(0)
        cmd = f"npx --no-install tsx {script}"
        if cmd not in commands:
            commands.append(cmd)
    goal = truncate_text(
        goal_hint.strip()
        or " ".join(str(reply_text or "").split())[:280]
        or "Execute scoped terminal work blocked on the prior shift",
        max_len=420,
    )
    return goal, commands[:3]


def _employee_id_for_role(workspace_id: str, role: str) -> str | None:
    from app.workspace_agents import build_company_roster

    role_clean = str(role or "").strip().lower()
    try:
        company = build_company_roster(workspace_id)
    except Exception:  # noqa: BLE001
        return None
    for row in company.get("employees") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("role") or "").strip().lower() == role_clean:
            employee_id = str(row.get("employee_id") or "").strip()
            return employee_id or None
    return None


def find_open_routed_terminal_task(
    workspace_id: str,
    owner_role: str,
) -> dict[str, Any] | None:
    """Newest open scoped-terminal ticket routed for this role."""
    role = str(owner_role or "").strip().lower()
    if not role:
        return None
    for task in task_store.list_tasks(workspace_id=workspace_id, owner_role=role, limit=30):
        goal = str(task.get("goal") or "")
        status = str(task.get("status") or "").strip().lower()
        if status not in {"open", "leased"}:
            continue
        if "scoped terminal follow-up" in goal.lower() and "[routed from" in goal.lower():
            return task
    return None


def _employee_for_role(workspace_id: str, role: str) -> tuple[str, str]:
    from app.workspace_agents import build_company_roster

    role_clean = str(role or "").strip().lower()
    try:
        company = build_company_roster(workspace_id)
    except Exception:  # noqa: BLE001
        return role_clean.title(), role_clean
    for row in company.get("employees") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("role") or "").strip().lower() == role_clean:
            name = str(row.get("name") or role_clean).strip() or role_clean.title()
            return name, role_clean
    return role_clean.title(), role_clean


def _post_assignment_notice(
    *,
    workspace_id: str,
    thread_id: str,
    assignee_name: str,
    assignee_role: str,
    goal: str,
    task_id: str,
    run_id: str | None,
    state: str,
    lead_name: str,
    routed_from: str,
) -> None:
    from datetime import datetime, timezone

    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    title = assignment_card_title(
        assignee_name=assignee_name,
        assignee_role=assignee_role,
        state=state,
    )
    body = assignment_card(
        assignee_name=assignee_name,
        assignee_role=assignee_role,
        goal=goal,
        task_id=task_id,
        run_id=run_id,
        state=state,
        lead_name=lead_name,
    )
    route_note = (
        f"Smart-routed from {routed_from}: prior shift lacked terminal scope or hit sandbox "
        f"limits — {assignee_name} owns the scoped follow-up."
    )
    chat_store.save_message(
        {
            "message_id": f"message_route_{uuid4().hex}",
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": run_id,
            "role": "system",
            "speaker_name": lead_name,
            "content": f"{title}\n\n{body}\n\n{route_note}",
            "created_at": created_at,
        }
    )


def try_route_capability_handoff(
    *,
    workspace_id: str,
    source_run_id: str,
    source_role: str,
    source_name: str,
    reply_text: str | None = None,
    blockers: str = "",
    goal_hint: str = "",
    command: str = "",
    block_reason: str = "",
) -> dict[str, Any] | None:
    """Create a scoped task for a capable agent and autostart when possible."""
    workspace = str(workspace_id or "").strip()
    cleaned_run = str(source_run_id or "").strip()
    if not workspace or not cleaned_run:
        return None
    source_run = run_store.get_run(cleaned_run)
    source_summary = str((source_run or {}).get("summary") or "").lower()
    # A routed follow-up must not route the same terminal denial into another
    # routed follow-up. That chain creates unbounded tasks and failure alerts.
    if "scoped terminal follow-up" in source_summary:
        logger.warning(
            "capability route cycle suppressed for run=%s workspace=%s",
            cleaned_run,
            workspace,
        )
        return None

    blob = " ".join(
        part.strip()
        for part in (blockers, block_reason, goal_hint, reply_text or "")
        if part and part.strip()
    )
    if not looks_like_terminal_capability_handoff(
        reply_text=reply_text,
        blockers=blockers,
        goal_hint=f"{goal_hint} {block_reason}",
    ) and not block_reason.strip():
        return None

    capability = _capability_kind(blob=blob, command=command)
    target_role = _pick_target_role(source_role=source_role, capability=capability)
    goal, commands = _extract_goal_and_commands(
        reply_text=reply_text,
        goal_hint=goal_hint,
        command=command,
    )
    command_hint = (
        "; ".join(f"`{item}`" for item in commands)
        if commands
        else "`axon-agent-terminal-job --workspace … -- <command>`"
    )
    acceptance = truncate_text(
        f"Run scoped terminal commands and attach stdout receipts: {command_hint}. "
        f"Use axon-agent-terminal-job for each command. [routed from {cleaned_run}]",
        max_len=480,
    )
    allowed_paths = ["services", "services/ops", "supabase", "tests"]
    if capability == "document_scope":
        allowed_paths = list(_DOCUMENT_ALLOWED_PATHS)
    elif target_role == "integrations":
        allowed_paths = ["services", "scripts", "tests"]

    for task in task_store.list_tasks(workspace_id=workspace, limit=40):
        existing_goal = str(task.get("goal") or "")
        if cleaned_run in existing_goal and "[routed from" in existing_goal.lower():
            if str(task.get("status") or "").lower() in {"open", "leased"}:
                return {
                    "status": "existing",
                    "task_id": task.get("task_id"),
                    "target_role": target_role,
                    "capability": capability,
                }

    try:
        created = task_store.create_task(
            workspace_id=workspace,
            goal=truncate_text(
                f"Scoped terminal follow-up ({target_role}): {goal} [routed from {cleaned_run}]",
                max_len=420,
            ),
            acceptance_criteria=acceptance,
            owner_role=target_role,
            allowed_paths=allowed_paths,
            risk="normal",
        )
    except task_store.TaskLedgerError as exc:
        logger.warning("capability route task create failed: %s", exc)
        return None

    task_id = str(created.get("task_id") or "").strip()
    if not task_id:
        return None

    target_name, _ = _employee_for_role(workspace, target_role)
    lead_name, _ = _employee_for_role(workspace, "lead")
    employee_id = _employee_id_for_role(workspace, target_role)
    thread = (
        chat_store.find_thread_for_employee(
            workspace,
            employee_id=employee_id,
            thread_kind="ide",
        )
        if employee_id
        else None
    )
    if thread is not None:
        _post_assignment_notice(
            workspace_id=workspace,
            thread_id=str(thread.get("thread_id") or ""),
            assignee_name=target_name,
            assignee_role=target_role,
            goal=goal,
            task_id=task_id,
            run_id=None,
            state="queued",
            lead_name=lead_name,
            routed_from=source_name or source_role,
        )

    from app.runs.service import append_run_execution_receipt

    append_run_execution_receipt(
        cleaned_run,
        receipt_type="capability_routed",
        receipt_summary=(
            f"Smart-routed terminal work to {target_name} ({target_role}) "
            f"task={task_id} capability={capability}"
        ),
        actor="capability_routing",
        success=True,
        intent="agent_handoff",
    )

    autostart: dict[str, Any] | None = None
    try:
        from app.workspace_handoff_routing import try_autostart_handoff_task

        autostart = try_autostart_handoff_task(task_id)
    except Exception as exc:  # noqa: BLE001
        logger.info("capability route autostart deferred for %s: %s", task_id, exc)

    if thread is not None and autostart is not None:
        run_id = str(autostart.get("run_id") or "").strip()
        if run_id:
            _post_assignment_notice(
                workspace_id=workspace,
                thread_id=str(thread.get("thread_id") or ""),
                assignee_name=target_name,
                assignee_role=target_role,
                goal=goal,
                task_id=task_id,
                run_id=run_id,
                state="started",
                lead_name=lead_name,
                routed_from=source_name or source_role,
            )

    return {
        "status": "routed",
        "task_id": task_id,
        "target_role": target_role,
        "target_name": target_name,
        "capability": capability,
        "autostart": autostart,
    }


def try_route_on_terminal_denial(
    *,
    workspace_id: str,
    run_id: str,
    role: str,
    command: str,
    reason: str,
) -> dict[str, Any] | None:
    """Best-effort route when agent terminal policy denies a command."""
    from app.workspace_agents import build_company_roster

    name = role
    try:
        for row in build_company_roster(workspace_id).get("employees") or []:
            if str(row.get("role") or "").strip().lower() == str(role or "").strip().lower():
                name = str(row.get("name") or role).strip() or role
                break
    except Exception:  # noqa: BLE001
        pass
    return try_route_capability_handoff(
        workspace_id=workspace_id,
        source_run_id=run_id,
        source_role=role,
        source_name=name,
        command=command,
        block_reason=reason,
        goal_hint=command,
    )


__all__ = [
    "find_open_routed_terminal_task",
    "looks_like_terminal_capability_handoff",
    "try_route_capability_handoff",
    "try_route_on_terminal_denial",
]
