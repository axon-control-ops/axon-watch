"""Resolve worker policy inputs and produce auditable run-safe receipts."""

from __future__ import annotations

import logging

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from app.project_contract.loader import ProjectContractError
from app.runs.service import append_run_execution_receipt
from app.workspace_agents.config_loader import EmployeeConfig
from app.workspace_agents.execution_policy import AgentExecutionPolicy, resolve_effective_policy
from app.workspace_agents.verifier_checks import load_repo_contract


logger = logging.getLogger(__name__)


def resolve_worker_execution_policy(
    *,
    employee: EmployeeConfig,
    task_payload: dict[str, Any],
    workspace_root: Path,
    workspace_id: str | None = None,
) -> AgentExecutionPolicy:
    """Resolve role, employee, and repository authority fail closed.

    The contract is read from the **bound workspace root** when one is known,
    falling back to ``workspace_root`` (usually the disposable checkout).

    Bound-first is the safer source, not the looser one:

    * ``create_isolation_root`` guarantees it never writes into the bound
      project, so the bound copy is the one tree an agent provably cannot
      author. A checkout, by contrast, is writable within the run's scope.
    * The contract is operator policy about what agents may do, not run
      content, so it belongs with the operator rather than with whatever
      commit a worktree happens to be pinned at.
    * A checkout only carries *committed* files. An untracked or uncommitted
      ``project.axon.yaml`` was therefore invisible to every run, which
      silently emptied the workspace scope and made the whole workspace
      read-only — with the agent appearing to refuse work.

    Gate 6's verifier contract deliberately still reads from the checkout: its
    checks describe the snapshot under review, whereas write authority
    describes present operator intent.
    """
    contract_source: Path = Path(workspace_root)
    if workspace_id:
        try:
            from app.terminal.workspace_roots import resolve_workspace_root

            bound_root = resolve_workspace_root(workspace_id)
            if bound_root.is_dir():
                contract_source = bound_root
        except Exception:  # noqa: BLE001 — fall back to the checkout, never fail dispatch
            contract_source = Path(workspace_root)
    try:
        contract = load_repo_contract(str(contract_source))
    except (OSError, ProjectContractError, ValueError) as exc:
        # An invalid contract silently becomes an empty workspace scope, which
        # intersects every role's write paths down to nothing. The ordinary
        # tool policy remains available for diagnosis, but the checkout gets no
        # role write mounts. Say that out loud instead of silently pretending
        # the task itself was the blocker.
        logger.warning(
            "project contract failed to load for %s (%s: %s); "
            "workspace scope is empty, so this run will be read-only",
            contract_source,
            type(exc).__name__,
            exc,
        )
        contract = {}
    task_paths = task_payload.get("allowed_paths")
    # Task paths are retained as routing/receipt metadata. They do not grant or
    # remove authority; role, explicit employee policy, and repository contract
    # are the enforcement inputs.
    task_scope = task_paths if isinstance(task_paths, list) and task_paths else None
    policy = resolve_effective_policy(
        role=employee.role,
        employee_override=employee.execution_policy,
        workspace_allowed_paths=contract.get("allowed_paths")
        if isinstance(contract.get("allowed_paths"), list)
        else (),
        workspace_forbidden_path_globs=contract.get("forbidden_path_globs")
        if isinstance(contract.get("forbidden_path_globs"), list)
        else (),
        task_allowed_paths=task_scope,
    )
    from app.workspace_agents.lead_verification_handoff import (
        is_verification_task,
        verification_approved_command_prefixes,
    )

    if is_verification_task(task_payload):
        extra = verification_approved_command_prefixes()
        merged = tuple(
            dict.fromkeys((*policy.approved_command_prefixes, *extra))
        )
        policy = replace(policy, approved_command_prefixes=merged)
    # Live-service policy is a widening enhancement on top of the baseline
    # policy above, resolved by walking every operator-maintained workspace
    # binding. That loader deliberately raises WorkspaceBindingError for a
    # binding outside the project-root allowlist (a real security config
    # error), which is the right contract for callers that need to trust the
    # binding -- but here it means one unrelated misconfigured workspace
    # (audio-transcribe, in the case that broke this) crashed policy
    # resolution for every other employee run in the fleet. Widening must
    # never be able to take down the baseline it is widening.
    try:
        scoped_workspace = str(workspace_id or "").strip()
        if not scoped_workspace:
            from app.workspace_service_connections import workspace_id_for_project_root

            scoped_workspace = workspace_id_for_project_root(workspace_root) or ""
        if scoped_workspace:
            from app.workspace_service_connections import apply_live_service_policy

            policy = apply_live_service_policy(
                policy,
                workspace_id=scoped_workspace,
                role=employee.role,
            )
    except Exception:  # noqa: BLE001 — an enhancement must degrade, never crash the baseline
        logger.exception(
            "live-service policy widening failed for workspace_root=%s; using baseline policy",
            workspace_root,
        )
    return policy


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
        "allow_all_tools": policy.allow_all_tools,
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
