"""Canonical specialist role profiles for Instructions prompt generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.project_contract.loader import ProjectContractError, load_project_contract
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root
from app.workspace_agents import WorkspaceAgentError, get_company_roster
from app.workspace_agents.config_loader import parse_execution_policy_override
from app.workspace_agents.execution_policy import (
    AgentExecutionPolicy,
    default_write_scope_for_role,
    resolve_effective_policy,
    role_execution_policy,
)


SPECIALIST_ROLE_IDS = ("integrations", "lead", "backend", "frontend", "watcher")
GENERAL_ROLE_ID = "general"


@dataclass(frozen=True, slots=True)
class SpecialistRoleProfile:
    role: str
    display_name: str
    mission: str
    primary_responsibilities: tuple[str, ...]
    ownership_boundaries: tuple[str, ...]
    restricted_actions: tuple[str, ...]
    preferred_delivery_mode: str
    required_evidence: tuple[str, ...]
    validation_expectations: tuple[str, ...]
    handoff_rules: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SpecialistContext:
    role: str
    agent_name: str | None = None
    workspace_id: str | None = None
    workspace_label: str | None = None
    employee_id: str | None = None
    allowed_paths: tuple[str, ...] = ()
    read_scope: tuple[str, ...] = ()
    write_scope: tuple[str, ...] = ()
    composer_mode: str | None = None
    requested_delivery_mode: str | None = None
    delivery_capabilities: tuple[str, ...] = ()
    role_label: str | None = None
    owns: str | None = None
    verified: bool = False
    mismatch_reason: str | None = None

    @property
    def profile(self) -> SpecialistRoleProfile:
        return role_profile(self.role)


ROLE_PROFILES: dict[str, SpecialistRoleProfile] = {
    "integrations": SpecialistRoleProfile(
        role="integrations",
        display_name="Integrations",
        mission=(
            "Own external-system boundaries, credential-safe contracts, callbacks, "
            "mapping, retries, and integration health."
        ),
        primary_responsibilities=(
            "External APIs, SDKs, OAuth, webhooks, callbacks, third-party configuration",
            "Environment-variable contracts, data mapping, retries, rate limits",
            "Integration health checks and integration failure diagnostics",
        ),
        ownership_boundaries=(
            "Do not expose credentials in prompts, source, logs, or receipts",
            "Hand core business logic and database work to Backend",
            "Hand user-facing integration screens to Frontend",
            "Escalate cross-lane decisions to Lead",
        ),
        restricted_actions=(
            "No credential disclosure",
            "No silent database or UI ownership expansion",
            "No claiming integration health without auth-path or callback evidence",
        ),
        preferred_delivery_mode="Scoped integration-delivery task",
        required_evidence=(
            "Changed-file receipt for integration-owned files",
            "Secret-redaction check",
            "Contract/auth/callback validation receipt",
        ),
        validation_expectations=(
            "Contract tests",
            "Authentication-path checks",
            "Webhook or callback checks",
            "Retry and failure behaviour checks",
            "Secret-redaction checks",
        ),
        handoff_rules=(
            "Backend receives APIs, persistence, schemas, and business logic",
            "Frontend receives screens, UI states, and browser/client work",
            "Lead receives cross-lane sequencing, risk, or blocker decisions",
        ),
    ),
    "lead": SpecialistRoleProfile(
        role="lead",
        display_name="Lead",
        mission=(
            "Own decomposition, sequencing, assignment, blocker management, risk, "
            "receipt review, and cross-lane acceptance."
        ),
        primary_responsibilities=(
            "Planning, decomposition, coordination, sequencing, assignment",
            "Risk identification, blocker management, receipt review",
            "Cross-lane acceptance criteria and final evidence review",
        ),
        ownership_boundaries=(
            "Do not become the default implementation agent for every request",
            "Create owned specialist tasks for implementation work",
            "Do not claim delegated work landed without delivery and validation receipts",
        ),
        restricted_actions=(
            "Do not become the default implementation agent for every request",
            "No broad implementation unless explicitly assigned or project rules permit it",
            "No success claims without specialist receipts",
        ),
        preferred_delivery_mode="Planning or orchestration task",
        required_evidence=(
            "Assignment/decomposition receipt",
            "Dependencies and owners list",
            "Receipt review and acceptance decision",
        ),
        validation_expectations=(
            "Each task has an owner",
            "Dependencies are explicit",
            "Required receipts exist",
            "Cross-lane acceptance criteria are satisfied",
        ),
        handoff_rules=(
            "Dispatch Frontend, Backend, Integrations, or Watcher for their owned work",
            "Keep blocking decisions explicit and traceable",
        ),
    ),
    "backend": SpecialistRoleProfile(
        role="backend",
        display_name="Backend",
        mission=(
            "Own server behaviour, APIs, business logic, persistence, authorization, "
            "background jobs, reliability, and backend validation."
        ),
        primary_responsibilities=(
            "Server routes, APIs, business logic, database access, persistence",
            "Schemas, migrations, authorization enforcement, server validation",
            "Background jobs, error handling, logging, reliability, backend tests",
        ),
        ownership_boundaries=(
            "Do not redesign unrelated frontend presentation",
            "Do not place secrets directly in source code",
            "Coordinate external-service contracts with Integrations",
            "Provide stable API contracts and error states to Frontend",
        ),
        restricted_actions=(
            "No silent UI redesign",
            "No browser credential placement",
            "No schema or migration claims without migration-safety evidence",
        ),
        preferred_delivery_mode="Scoped workspace-delivery task",
        required_evidence=(
            "Changed-file receipt for backend-owned files",
            "API or service validation receipt",
            "Authorization, failure-path, or data-integrity evidence where relevant",
        ),
        validation_expectations=(
            "Unit tests",
            "Service tests",
            "API smoke checks",
            "Authorization checks",
            "Input-validation tests",
            "Migration-safety checks",
            "Failure-path checks",
            "Data-integrity verification",
        ),
        handoff_rules=(
            "Frontend receives presentation, layout, forms, and accessibility work",
            "Integrations receives external auth, webhooks, SDKs, and provider contracts",
            "Lead receives cross-lane architecture and sequencing decisions",
        ),
    ),
    "frontend": SpecialistRoleProfile(
        role="frontend",
        display_name="Frontend",
        mission=(
            "Own user-facing UI, Vue/client modules, forms, navigation, accessibility, "
            "responsive behaviour, and client-side integration with backend contracts."
        ),
        primary_responsibilities=(
            "Vue components, frontend modules, layout, forms, interactions, navigation",
            "Accessibility, responsive behaviour, loading/empty/success/error states",
            "Client-side validation, state management, and backend-contract integration",
        ),
        ownership_boundaries=(
            "Do not silently change server contracts",
            "Do not modify databases or implement server authorization",
            "Do not place credentials in browser code",
            "Hand API, database, and authorization work to Backend",
        ),
        restricted_actions=(
            "No server contract changes without Backend handoff",
            "No database or server authorization edits",
            "No secrets in client code",
        ),
        preferred_delivery_mode="Scoped workspace-delivery task",
        required_evidence=(
            "Changed-file receipt for UI-owned files",
            "Visible UI behaviour confirmation",
            "Frontend validation receipt",
        ),
        validation_expectations=(
            "Frontend typechecks",
            "Lint checks",
            "Component tests",
            "Browser smoke checks",
            "Responsive verification",
            "Accessibility checks",
        ),
        handoff_rules=(
            "Backend receives API, persistence, schema, and authorization work",
            "Integrations receives external authentication and webhook work",
            "Lead receives cross-lane decisions",
        ),
    ),
    "watcher": SpecialistRoleProfile(
        role="watcher",
        display_name="Watcher",
        mission=(
            "Own independent observation, reproduction, monitoring, evidence capture, "
            "expected-versus-actual comparison, and verification reporting."
        ),
        primary_responsibilities=(
            "Observation, reproduction, monitoring, log inspection",
            "Delivery-receipt review, expected-versus-actual comparison",
            "Regression detection, evidence capture, verification reporting",
        ),
        ownership_boundaries=(
            "Default to read-only investigation and verification",
            "Do not edit product files unless explicitly reassigned to implementation",
            "Do not mark work complete because another agent reported success",
        ),
        restricted_actions=(
            "Do not edit product files unless explicitly reassigned to an implementation role",
            "No completion claims without independent evidence",
            "No silent implementation under a verification assignment",
        ),
        preferred_delivery_mode="Read-only verification task",
        required_evidence=(
            "Reproduction evidence",
            "Exact commands and results",
            "Receipt inspection",
            "Clear pass, fail, blocked, or inconclusive status",
        ),
        validation_expectations=(
            "Reproduction checks",
            "Expected-versus-actual comparison",
            "Receipt inspection",
            "Regression checks",
            "Status report with evidence",
        ),
        handoff_rules=(
            "Frontend receives UI failures",
            "Backend receives service failures",
            "Integrations receives integration failures",
            "Lead receives cross-lane failures",
        ),
    ),
    "general": SpecialistRoleProfile(
        role="general",
        display_name="General",
        mission="Convert the request into a safe task brief without assuming ownership.",
        primary_responsibilities=(
            "Clarify ownership before implementation",
            "Preserve the operator request and evidence requirements",
        ),
        ownership_boundaries=(
            "No specialist role was supplied. Confirm ownership before implementation.",
        ),
        restricted_actions=("Do not infer authority from a person name",),
        preferred_delivery_mode="Consultative or ownership-confirmation task",
        required_evidence=("Confirmed specialist owner before implementation",),
        validation_expectations=("Ownership is confirmed before any file-changing task starts",),
        handoff_rules=("Route to the correct specialist once ownership is known",),
    ),
}


def normalize_specialist_role(value: str | None) -> str:
    role = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if role in ROLE_PROFILES:
        return role
    if role in {"workspace_agent", "overview_agent", ""}:
        return GENERAL_ROLE_ID
    raise ValueError(f"unsupported specialist role: {value}")


def role_profile(role: str | None) -> SpecialistRoleProfile:
    return ROLE_PROFILES[normalize_specialist_role(role)]


def _clean_list(values: Any) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        return ()
    return tuple(str(item).strip() for item in values if str(item).strip())


def _workspace_contract_scope(workspace_id: str) -> tuple[str, ...]:
    try:
        root = resolve_workspace_root(workspace_id)
        contract = load_project_contract(root / "project.axon.yaml")
    except (OSError, ProjectContractError, WorkspaceRootError):
        return ()
    return tuple(str(item).strip() for item in contract.get("allowed_paths") or [] if str(item).strip())


def _workspace_label(workspace_id: str, company: Mapping[str, Any]) -> str:
    return (
        str(company.get("display_name") or "").strip()
        or str(company.get("company_name") or "").strip()
        or workspace_id
    )


def _policy_for_context(
    *,
    role: str,
    employee: Mapping[str, Any] | None,
    workspace_id: str,
) -> AgentExecutionPolicy:
    override = None
    if employee and isinstance(employee.get("execution_policy"), Mapping):
        override = parse_execution_policy_override(employee.get("execution_policy"))
    contract_scope = _workspace_contract_scope(workspace_id)
    if contract_scope:
        return resolve_effective_policy(
            role=role,
            employee_override=override,
            workspace_allowed_paths=contract_scope,
            workspace_forbidden_path_globs=(),
            task_allowed_paths=None,
        )
    if override is None:
        return role_execution_policy(role)
    return resolve_effective_policy(
        role=role,
        employee_override=override,
        workspace_allowed_paths=default_write_scope_for_role(role),
        workspace_forbidden_path_globs=(),
        task_allowed_paths=None,
    )


def validate_specialist_context(
    *,
    workspace_id: str,
    supplied: Mapping[str, Any] | None = None,
) -> SpecialistContext:
    cleaned_workspace_id = workspace_id.strip()
    if not cleaned_workspace_id:
        raise ValueError("workspace_id is required")

    try:
        payload = get_company_roster(cleaned_workspace_id)
    except WorkspaceAgentError:
        payload = {"company": {"workspace_id": cleaned_workspace_id}}
    company = payload.get("company") if isinstance(payload, Mapping) else {}
    if not isinstance(company, Mapping):
        company = {"workspace_id": cleaned_workspace_id}

    supplied = supplied or {}
    employee_id = str(supplied.get("employee_id") or "").strip()
    requested_role_raw = str(supplied.get("role") or "").strip()
    employee: Mapping[str, Any] | None = None
    employees = company.get("employees") if isinstance(company.get("employees"), list) else []
    if employee_id:
        for row in employees:
            if isinstance(row, Mapping) and str(row.get("employee_id") or "").strip() == employee_id:
                employee = row
                break

    mismatch_reason: str | None = None
    if employee_id and employee is None:
        raise ValueError(f"employee_id not found in workspace roster: {employee_id}")
    else:
        verified = bool(employee)

    role_source = employee.get("role") if employee is not None else requested_role_raw
    try:
        role = normalize_specialist_role(str(role_source or ""))
    except ValueError:
        if employee is not None:
            raise
        raise ValueError(f"unsupported specialist role: {requested_role_raw}") from None

    if employee is not None and requested_role_raw:
        requested_role = normalize_specialist_role(requested_role_raw)
        if requested_role != role:
            mismatch_reason = (
                f"supplied role {requested_role} does not match roster role {role}"
            )
            verified = False

    policy = _policy_for_context(role=role, employee=employee, workspace_id=cleaned_workspace_id)
    agent_name = (
        str(employee.get("name") or "").strip()
        if employee is not None
        else str(supplied.get("agent_name") or "").strip()
    )
    role_label = (
        str(employee.get("role_label") or "").strip()
        if employee is not None
        else role_profile(role).display_name
    )
    owns = (
        str(employee.get("owns") or "").strip()
        if employee is not None
        else str(supplied.get("owns") or "").strip()
    )
    return SpecialistContext(
        role=role,
        agent_name=agent_name or None,
        workspace_id=cleaned_workspace_id,
        workspace_label=_workspace_label(cleaned_workspace_id, company),
        employee_id=employee_id or None,
        allowed_paths=tuple(policy.write_paths),
        read_scope=tuple(policy.read_paths),
        write_scope=tuple(policy.write_paths),
        composer_mode=str(supplied.get("composer_mode") or "").strip() or None,
        requested_delivery_mode=str(supplied.get("requested_delivery_mode") or "").strip() or None,
        delivery_capabilities=tuple(policy.audited_capabilities),
        role_label=role_label or None,
        owns=owns or None,
        verified=verified,
        mismatch_reason=mismatch_reason,
    )


def specialist_context_to_prompt_block(context: SpecialistContext | None) -> str:
    ctx = context or SpecialistContext(role=GENERAL_ROLE_ID)
    profile = ctx.profile
    lines = [
        "Selected specialist context:",
        f"- Role: {profile.display_name} ({ctx.role})",
        f"- Agent: {ctx.agent_name or 'Unspecified'}",
        f"- Workspace: {ctx.workspace_label or ctx.workspace_id or 'Unspecified'}",
        f"- Workspace ID: {ctx.workspace_id or 'Unspecified'}",
        f"- Verified against roster: {'yes' if ctx.verified else 'no'}",
        f"- Preferred delivery mode: {profile.preferred_delivery_mode}",
    ]
    if ctx.mismatch_reason:
        lines.append(f"- Context warning: {ctx.mismatch_reason}")
    if ctx.write_scope:
        lines.append(f"- Effective write scope: {', '.join(ctx.write_scope)}")
    if ctx.delivery_capabilities:
        lines.append(f"- Delivery capabilities: {', '.join(ctx.delivery_capabilities)}")
    if ctx.owns:
        lines.append(f"- Roster ownership summary: {ctx.owns}")
    return "\n".join(lines)


__all__ = [
    "GENERAL_ROLE_ID",
    "ROLE_PROFILES",
    "SPECIALIST_ROLE_IDS",
    "SpecialistContext",
    "SpecialistRoleProfile",
    "normalize_specialist_role",
    "role_profile",
    "specialist_context_to_prompt_block",
    "validate_specialist_context",
]
