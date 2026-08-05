"""Resolve worker policy inputs and produce auditable run-safe receipts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.project_contract.loader import ProjectContractError
from app.runs.service import append_run_execution_receipt
from app.workspace_agents.config_loader import EmployeeConfig
from app.workspace_agents.execution_policy import AgentExecutionPolicy, resolve_effective_policy
from app.workspace_agents.verifier_checks import load_repo_contract


def resolve_worker_execution_policy(
    *,
    employee: EmployeeConfig,
    task_payload: dict[str, Any],
    workspace_root: Path,
) -> AgentExecutionPolicy:
    """Resolve role, employee, contract, and leased-task scope fail closed."""
    try:
        contract = load_repo_contract(str(workspace_root))
    except (OSError, ProjectContractError, ValueError):
        contract = {}
    task_paths = task_payload.get("allowed_paths")
    return resolve_effective_policy(
        role=employee.role,
        employee_override=employee.execution_policy,
        workspace_allowed_paths=contract.get("allowed_paths")
        if isinstance(contract.get("allowed_paths"), list)
        else (),
        workspace_forbidden_path_globs=contract.get("forbidden_path_globs")
        if isinstance(contract.get("forbidden_path_globs"), list)
        else (),
        task_allowed_paths=task_paths if isinstance(task_paths, list) else (),
    )


def execution_policy_payload(policy: AgentExecutionPolicy) -> dict[str, Any]:
    """Serialize only policy authority; never include environment or credentials."""
    return {
        "read_paths": list(policy.read_paths),
        "write_paths": list(policy.write_paths),
        "forbidden_path_globs": list(policy.forbidden_path_globs),
        "approved_wrappers": list(policy.approved_wrapper_names),
        "approved_command_prefixes": [
            list(prefix) for prefix in policy.approved_command_prefixes
        ],
        "audited_capabilities": list(policy.audited_capabilities),
        "network_mode": policy.network_mode,
        "timeout_seconds": policy.timeout_seconds,
        "trust_policy": policy.trust_policy,
        "execution_access": policy.execution_access,
    }


def execution_policy_identity(policy: AgentExecutionPolicy) -> str:
    encoded = json.dumps(
        execution_policy_payload(policy),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "policy-" + hashlib.sha256(encoded).hexdigest()[:20]


def record_execution_policy_receipt(run_id: str, policy: AgentExecutionPolicy) -> str:
    identity = execution_policy_identity(policy)
    writes = ",".join(policy.write_paths) or "read-only"
    append_run_execution_receipt(
        run_id,
        receipt_type="agent_execution_policy",
        receipt_summary=(
            f"{identity} access={policy.execution_access} writes={writes} "
            f"network={policy.network_mode} timeout={policy.timeout_seconds}s"
        ),
        actor="workspace_scheduler",
        success=True,
        intent="sandbox_policy",
    )
    return identity


__all__ = [
    "execution_policy_identity",
    "execution_policy_payload",
    "record_execution_policy_receipt",
    "resolve_worker_execution_policy",
]
