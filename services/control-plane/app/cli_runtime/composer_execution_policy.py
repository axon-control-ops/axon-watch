"""Bounded Full Access policy for the operator's disposable composer checkout."""

from __future__ import annotations

from pathlib import Path

from app.project_contract.loader import ProjectContractError
from app.workspace_agents.execution_policy import AgentExecutionPolicy, role_execution_policy
from app.workspace_agents.execution_policy_prefixes import (
    COMMON_AUDITED_WRAPPERS,
    COMMON_READ_PREFIXES,
    GH_READ_PREFIXES,
    VALIDATION_PREFIXES,
)
from app.workspace_agents.verifier_checks import load_repo_contract

_SECRET_GLOBS = (
    ".env", ".env.*", "**/.env", "**/.env.*", "**/.secrets/**",
    "**/secrets/**", "**/credentials/**", "**/*credentials.json",
)


def operator_composer_sandbox_policy(workspace_root: Path) -> AgentExecutionPolicy:
    """Allow routine local work across the disposable copy; deny implicit high-risk effects."""
    try:
        contract = load_repo_contract(str(workspace_root))
    except (OSError, ProjectContractError, ValueError):
        contract = {}
    configured = contract.get("forbidden_path_globs")
    forbidden = tuple(dict.fromkeys((*_SECRET_GLOBS, *(
        str(item) for item in configured if str(item).strip()
    )))) if isinstance(configured, list) else _SECRET_GLOBS
    return AgentExecutionPolicy(
        read_paths=(".",),
        write_paths=(".",),
        forbidden_path_globs=forbidden,
        approved_wrapper_names=COMMON_AUDITED_WRAPPERS,
        approved_command_prefixes=(*COMMON_READ_PREFIXES, *VALIDATION_PREFIXES, *GH_READ_PREFIXES),
        audited_capabilities=("workspace_read", "workspace_write", "test", "ci_read"),
        network_mode="audited",
        timeout_seconds=1200,
        trust_policy="operator",
        execution_access="full",
    )


def resolve_composer_execution_policy(
    workspace_root: Path | None, employee_role: str, composer_mode: str
) -> AgentExecutionPolicy | None:
    from app.cli_runtime.approval_gate import is_tool_capable_composer_mode

    if not is_tool_capable_composer_mode(composer_mode):
        return None
    if employee_role:
        return role_execution_policy(employee_role)
    return operator_composer_sandbox_policy(workspace_root) if workspace_root is not None else None


__all__ = ["operator_composer_sandbox_policy", "resolve_composer_execution_policy"]
