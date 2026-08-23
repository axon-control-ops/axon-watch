"""Server-side identity and command checks for agent-owned terminal jobs."""

from __future__ import annotations

from typing import Any

from app.cli_runtime.long_running_shell import is_long_running_ship_shell
from app.cli_runtime.agent_shell_hook import evaluate_hook_payload
from app.persistence import run_store, task_store
from app.runs.service import (
    RunNotFoundError,
    append_run_execution_receipt,
    get_run,
)
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root
from app.workspace_agents.config_loader import EmployeeConfig, load_workspace_agent_configs
from app.workspace_agents.execution_policy import role_execution_policy
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


def _resolve_scoped_task_for_run(
    *,
    workspace_id: str,
    role: str,
    run: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Backfill run.task_id from an open verification ticket when chat runs lack scope."""
    task_id = str(run.get("task_id") or "").strip()
    task = task_store.get_task(task_id) if task_id else None
    if task is not None:
        return task, run
    from app.workspace_agents.lead_verification_handoff import (
        find_open_verification_task,
        try_lease_open_verification_task,
    )

    candidate = find_open_verification_task(workspace_id, role)
    if candidate is None:
        from app.workspace_agents.capability_routing import find_open_routed_terminal_task

        candidate = find_open_routed_terminal_task(workspace_id, role)
    if candidate is None:
        from app.workspace_agents.specialist_task_scope import try_lease_open_specialist_task

        leased = try_lease_open_specialist_task(
            workspace_id=workspace_id,
            owner_role=role,
            lease_holder=f"agent-terminal-{workspace_id}-{role}",
            run_id=str(run.get("run_id") or "").strip() or None,
        )
        if leased is not None:
            candidate = leased
    if candidate is None:
        return None, run
    cleaned_run = str(run.get("run_id") or "").strip()
    holder = f"agent-terminal-{workspace_id}-{role}"
    leased = try_lease_open_verification_task(
        workspace_id=workspace_id,
        owner_role=role,
        lease_holder=holder,
        run_id=cleaned_run or None,
    )
    if leased is None:
        leased = candidate
    bound_task_id = str(leased.get("task_id") or "").strip()
    if not bound_task_id:
        return None, run
    updated = dict(run)
    if not task_id:
        updated["task_id"] = bound_task_id
        updated = run_store.save_run(updated)
    if str(leased.get("status") or "").strip().lower() == "leased" and cleaned_run:
        try:
            task_store.bind_task_run(bound_task_id, cleaned_run)
        except task_store.TaskLedgerError:
            pass
    stored = task_store.get_task(bound_task_id)
    return stored, updated


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
    task, run = _resolve_scoped_task_for_run(
        workspace_id=source,
        role=role,
        run=run,
    )
    try:
        root = resolve_workspace_root(workspace_id)
    except WorkspaceRootError as exc:
        raise AgentTerminalPolicyError(str(exc)) from exc
    if task is None:
        policy = role_execution_policy(role)
        if (
            policy.execution_access != "full"
            or role not in {"lead", "integrations"}
            or not is_long_running_ship_shell(command)
        ):
            from app.workspace_agents.capability_routing import try_route_on_terminal_denial

            routed = try_route_on_terminal_denial(
                workspace_id=source,
                run_id=clean_run,
                role=role,
                command=command,
                reason="agent terminal run has no scoped task",
            )
            if routed is not None:
                raise AgentTerminalPolicyError(
                    f"Smart-routed to scoped task {routed.get('task_id')} "
                    f"({routed.get('target_role')}); retry via assignment board"
                )
            raise AgentTerminalPolicyError("agent terminal run has no scoped task")
        append_run_execution_receipt(
            clean_run,
            receipt_type="agent_terminal_allowed",
            receipt_summary="Approved no-task ship terminal command accepted",
            actor="agent_terminal_policy",
            success=True,
            intent="terminal_command",
        )
        return role
    policy = resolve_worker_execution_policy(
        employee=_employee_for_role(source, role),
        task_payload=task,
        workspace_root=root,
        workspace_id=source,
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
        from app.workspace_agents.capability_routing import try_route_on_terminal_denial

        routed = try_route_on_terminal_denial(
            workspace_id=source,
            run_id=clean_run,
            role=role,
            command=command,
            reason=reason,
        )
        if routed is not None:
            raise AgentTerminalPolicyError(
                f"Smart-routed to scoped task {routed.get('task_id')} "
                f"({routed.get('target_role')}); use axon-agent-terminal-job on assignment"
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
