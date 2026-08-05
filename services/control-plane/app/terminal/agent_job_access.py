"""Server-side identity and command checks for agent-owned terminal jobs."""

from __future__ import annotations

from app.cli_runtime.agent_shell_hook import evaluate_hook_payload
from app.persistence import task_store
from app.runs.service import (
    RunNotFoundError,
    append_run_execution_receipt,
    get_run,
)
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root
from app.workspace_agents.config_loader import EmployeeConfig, load_workspace_agent_configs
from app.workspace_agents.execution_policy_runtime import resolve_worker_execution_policy


class AgentTerminalPolicyError(ValueError):
    """An agent terminal request lacks trusted identity, scope, or command authority."""


def _employee_for_role(workspace_id: str, role: str) -> EmployeeConfig:
    _configs, _defaults, companies, _staffing = load_workspace_agent_configs()
    company = companies.get(workspace_id)
    if company is not None:
        for employee in company.employees:
            if employee.role == role:
                return employee
    return EmployeeConfig(role=role)


def assert_agent_terminal_job_allowed(
    *,
    workspace_id: str,
    source_workspace_id: str | None,
    run_id: str | None,
    command: str,
) -> str | None:
    """Validate agent calls; absence of source identity denotes an operator call."""
    source = str(source_workspace_id or "").strip()
    if not source:
        return None
    clean_run = str(run_id or "").strip()
    if not clean_run:
        raise AgentTerminalPolicyError("agent terminal jobs require a trusted run_id")
    if source != workspace_id:
        raise AgentTerminalPolicyError("agent terminal jobs cannot target another workspace")
    try:
        run = get_run(clean_run)
    except RunNotFoundError as exc:
        raise AgentTerminalPolicyError("agent terminal run identity was not found") from exc
    if str(run.get("workspace_id") or "").strip() != source:
        raise AgentTerminalPolicyError("agent terminal source does not match its run")
    role = str(run.get("employee_role") or "").strip().lower()
    if not role:
        raise AgentTerminalPolicyError("agent terminal run has no employee role")
    task_id = str(run.get("task_id") or "").strip()
    task = task_store.get_task(task_id) if task_id else None
    if task is None:
        raise AgentTerminalPolicyError("agent terminal run has no scoped task")
    try:
        root = resolve_workspace_root(workspace_id)
    except WorkspaceRootError as exc:
        raise AgentTerminalPolicyError(str(exc)) from exc
    policy = resolve_worker_execution_policy(
        employee=_employee_for_role(source, role),
        task_payload=task,
        workspace_root=root,
    )
    decision = evaluate_hook_payload(
        {"hook_event_name": "beforeShellExecution", "command": command},
        approved_wrappers=frozenset(policy.approved_wrapper_names),
        approved_command_prefixes=policy.approved_command_prefixes,
    )
    if decision.get("permission") != "allow":
        reason = str(decision.get("agent_message") or "command denied")
        append_run_execution_receipt(
            clean_run,
            receipt_type="agent_terminal_denied",
            receipt_summary=reason,
            actor="agent_terminal_policy",
            success=False,
            intent="terminal_command",
        )
        raise AgentTerminalPolicyError(reason)
    append_run_execution_receipt(
        clean_run,
        receipt_type="agent_terminal_allowed",
        receipt_summary="Approved terminal wrapper command accepted",
        actor="agent_terminal_policy",
        success=True,
        intent="terminal_command",
    )
    return role


__all__ = ["AgentTerminalPolicyError", "assert_agent_terminal_job_allowed"]
