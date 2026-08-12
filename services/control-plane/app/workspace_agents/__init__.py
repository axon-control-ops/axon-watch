"""Workspace company roster — each workspace is a company with role-based employees."""

from __future__ import annotations

from app.workspace_agents.catalog import ROLE_CATALOG, WORKSPACE_AGENT_STATUSES, _DEFAULT_OWNS
from app.workspace_agents.config_loader import (
    CompanyConfig,
    EmployeeConfig,
    WorkspaceAgentConfig,
    WorkspaceAgentError,
    default_agents_file,
    load_workspace_agent_configs,
    _agent_id,
    _agent_key,
    _default_agent_name,
    _default_company_name,
    _default_employee_name,
    _display_name_for_workspace,
    _employee_id,
    _normalize_schedule,
    _resolve_employees,
    _role_label,
    _schedule_label,
    _title_display_name,
)
from app.persistence import worker_scheduler_settings_store
from app.workspace_agents.run_outcome import latest_role_run_outcome
from app.workspace_agents.status import (
    active_role_run_id,
    active_role_run_status,
    derive_agent_status,
    employee_status,
)
from app.workspace_catalog import WorkspaceNotFoundError, get_workspace_record, list_workspace_records
from app.workspace_project_bindings import load_workspace_project_bindings

__all__ = [
    "CompanyConfig",
    "EmployeeConfig",
    "ROLE_CATALOG",
    "WORKSPACE_AGENT_STATUSES",
    "WorkspaceAgentConfig",
    "WorkspaceAgentError",
    "build_company_roster",
    "build_company_roster_snapshot",
    "build_workspace_agent_record",
    "default_agents_file",
    "get_company_roster",
    "get_workspace_agent_record",
    "list_role_catalog",
    "list_workspace_agent_records",
    "load_workspace_agent_configs",
]


def _pending_decision_for_role(workspace_id: str, role: str) -> dict[str, object] | None:
    """Return the newest unresolved VAXON decision owned by this role."""
    try:
        from app.persistence import autonomous_attention_store

        for decision in autonomous_attention_store.list_pending_decisions(limit=100):
            if str(decision.get("workspace_id") or "").strip() != workspace_id:
                continue
            payload = decision.get("payload") if isinstance(decision.get("payload"), dict) else {}
            if str(payload.get("owner_role") or "").strip().lower() == role.lower():
                return decision
    except Exception:  # noqa: BLE001 — roster must stay available on attention-store issues
        return None
    return None


def build_company_roster(
    workspace_id: str,
    *,
    record: dict[str, str] | None = None,
    configs: dict[str, WorkspaceAgentConfig] | None = None,
    defaults: dict[str, str] | None = None,
    companies: dict[str, CompanyConfig] | None = None,
    staffing_template: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    workspace_record = record or get_workspace_record(workspace_id)
    normalized_id = workspace_id.strip()
    if configs is None or defaults is None or companies is None or staffing_template is None:
        configs, defaults, companies, staffing_template = load_workspace_agent_configs()

    display_name = _display_name_for_workspace(normalized_id, workspace_record)
    company = companies.get(normalized_id)
    legacy = configs.get(normalized_id)
    company_name = (
        (company.company_name if company else None)
        or _default_company_name(
            display_name,
            company_name_template=defaults.get("company_name_template", "{display_name}"),
        )
    )
    employees = _resolve_employees(
        normalized_id,
        display_name=display_name,
        company=company,
        legacy=legacy,
        defaults=defaults,
        staffing_template=staffing_template,
    )
    workspace_status = derive_agent_status(normalized_id)
    employee_rows: list[dict[str, object]] = []
    primary_employee_id: str | None = None

    for index, employee in enumerate(employees):
        role = employee.role or "workspace_agent"
        schedule = employee.schedule or _normalize_schedule(None, role=role)
        emp_id = employee.employee_id or _employee_id(normalized_id, role, index)
        name = employee.name or _default_employee_name(normalized_id, display_name, role)
        owns = employee.owns or _DEFAULT_OWNS.get(
            role,
            f"{_title_display_name(display_name)} assigned work only",
        )
        enabled = worker_scheduler_settings_store.is_employee_enabled(
            normalized_id,
            role,
            file_enabled=bool(employee.enabled),
        )
        status = employee_status(
            role=role,
            schedule=schedule,
            workspace_status=workspace_status,
            primary=employee.primary,
            role_run_status=active_role_run_status(normalized_id, role),
        )
        pending_decision = _pending_decision_for_role(normalized_id, role)
        # A Lead may have finished the safe portion of their run while a real
        # operator choice remains. Showing idle hid that state in the employee
        # strip; reflect the VAXON escalation until the decision is resolved.
        if pending_decision is not None:
            status = "waiting_approval"
        if employee.primary:
            primary_employee_id = emp_id
        outcome = latest_role_run_outcome(normalized_id, role)
        row: dict[str, object] = {
            "employee_id": emp_id,
            "workspace_id": normalized_id,
            "name": name,
            "role": role,
            "role_label": _role_label(role),
            "schedule": schedule,
            "schedule_label": _schedule_label(schedule),
            "status": status,
            "owns": owns,
            "enabled": enabled,
            "primary": employee.primary,
        }
        if employee.azure_voice_id:
            row["azure_voice_id"] = employee.azure_voice_id
        if outcome:
            row["last_outcome"] = outcome.get("outcome")
            row["last_outcome_detail"] = outcome.get("detail")
            row["last_run_id"] = outcome.get("run_id")
        active_run = active_role_run_id(normalized_id, role)
        if active_run:
            row["active_run_id"] = active_run
        if pending_decision is not None:
            decision_payload = (
                pending_decision.get("payload")
                if isinstance(pending_decision.get("payload"), dict)
                else {}
            )
            decision_options = (
                decision_payload.get("options")
                if isinstance(decision_payload.get("options"), list)
                else []
            )
            row["pending_decision_id"] = pending_decision.get("receipt_id")
            row["pending_decision_title"] = pending_decision.get("title")
            row["pending_decision_prompt"] = decision_payload.get("prompt")
            row["pending_decision_reason"] = pending_decision.get("detail")
            row["pending_decision_options"] = decision_options
        employee_rows.append(row)

    try:
        from app.workspace_delivery import store as delivery_store

        delivery = delivery_store.latest_workspace_delivery(normalized_id)
    except Exception:  # noqa: BLE001 — roster must not fail closed on delivery store
        delivery = None
    if delivery is not None:
        stage = str(delivery.get("stage") or "").strip()
        detail_bits = [
            bit
            for bit in (
                str(delivery.get("worker_branch") or "").strip(),
                str(delivery.get("draft_pr_url") or "").strip(),
                str(delivery.get("ci_conclusion") or "").strip(),
                str(delivery.get("blocker") or "").strip(),
            )
            if bit
        ]
        pipeline_detail = " · ".join(detail_bits) if detail_bits else stage
        draft_pr = str(delivery.get("draft_pr_url") or "").strip() or None
        ci_run_url = str(delivery.get("ci_run_url") or "").strip() or None
        ci_status = str(delivery.get("ci_conclusion") or stage or "").strip() or None
        for row in employee_rows:
            role = str(row.get("role") or "").strip().lower()
            if role in {"watcher", "integrations", "lead", "backend"}:
                row["pipeline_stage"] = stage or None
                row["pipeline_detail"] = pipeline_detail or None
                row["draft_pr_url"] = draft_pr
                row["ci_run_url"] = ci_run_url
                row["ci_status"] = ci_status

    if primary_employee_id is None and employee_rows:
        employee_rows[0]["primary"] = True
        primary_employee_id = str(employee_rows[0]["employee_id"])

    payload: dict[str, object] = {
        "workspace_id": normalized_id,
        "company_name": company_name,
        "employee_count": len(employee_rows),
        "employees": employee_rows,
        "primary_employee_id": primary_employee_id,
    }
    if workspace_record.get("display_name"):
        payload["display_name"] = workspace_record["display_name"]
    if workspace_record.get("project_root"):
        payload["project_root"] = workspace_record["project_root"]
    return payload


def build_company_roster_snapshot(workspace_id: str) -> dict[str, object]:
    return {
        "company": build_company_roster(workspace_id),
        "role_catalog": list(ROLE_CATALOG),
    }


def build_workspace_agent_record(
    workspace_id: str,
    *,
    record: dict[str, str] | None = None,
    configs: dict[str, WorkspaceAgentConfig] | None = None,
    defaults: dict[str, str] | None = None,
    companies: dict[str, CompanyConfig] | None = None,
    staffing_template: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Return the primary company employee as the legacy workspace-agent record."""
    workspace_record = record or get_workspace_record(workspace_id)
    normalized_id = workspace_id.strip()
    if configs is None or defaults is None or companies is None or staffing_template is None:
        configs, defaults, companies, staffing_template = load_workspace_agent_configs()

    roster = build_company_roster(
        normalized_id,
        record=workspace_record,
        configs=configs,
        defaults=defaults,
        companies=companies,
        staffing_template=staffing_template,
    )
    employees = roster.get("employees")
    primary: dict[str, object] | None = None
    if isinstance(employees, list):
        for row in employees:
            if isinstance(row, dict) and row.get("primary"):
                primary = row
                break
        if primary is None and employees and isinstance(employees[0], dict):
            primary = employees[0]

    display_name = _display_name_for_workspace(normalized_id, workspace_record)
    if primary is None:
        # Extremely defensive fallback.
        agent_name = _default_agent_name(
            display_name,
            name_template=defaults["name_template"],
        )
        payload: dict[str, object] = {
            "agent_id": _agent_id(normalized_id),
            "workspace_id": normalized_id,
            "agent_name": agent_name,
            "agent_key": _agent_key(normalized_id, display_name),
            "role": defaults.get("role", "workspace_agent"),
            "status": derive_agent_status(normalized_id),
            "owns": f"{display_name} assigned work only",
            "enabled": True,
            "schedule": "on_demand",
            "primary": True,
            "company_name": str(roster.get("company_name") or display_name),
        }
    else:
        payload = {
            "agent_id": _agent_id(normalized_id),
            "workspace_id": normalized_id,
            "agent_name": primary.get("name") or _default_agent_name(
                display_name,
                name_template=defaults["name_template"],
            ),
            "agent_key": _agent_key(normalized_id, display_name),
            "role": primary.get("role") or defaults.get("role", "workspace_agent"),
            "status": primary.get("status") or derive_agent_status(normalized_id),
            "owns": primary.get("owns") or f"{display_name} assigned work only",
            "enabled": bool(primary.get("enabled", True)),
            "schedule": primary.get("schedule") or "on_demand",
            "primary": True,
            "company_name": str(roster.get("company_name") or display_name),
        }

    if workspace_record.get("display_name"):
        payload["display_name"] = workspace_record["display_name"]
    if workspace_record.get("project_root"):
        payload["project_root"] = workspace_record["project_root"]
    return payload


def list_workspace_agent_records(
    *,
    operator_surface: bool = False,
) -> list[dict[str, object]]:
    configs, defaults, companies, staffing_template = load_workspace_agent_configs()
    workspace_records = list_workspace_records(operator_surface=operator_surface)
    bindings = load_workspace_project_bindings()

    agents: list[dict[str, object]] = []
    seen: set[str] = set()
    for record in workspace_records:
        workspace_id = str(record.get("workspace_id", "")).strip()
        if not workspace_id or workspace_id in seen:
            continue
        seen.add(workspace_id)
        legacy = configs.get(workspace_id)
        if legacy is not None and not legacy.enabled:
            continue
        agents.append(
            build_workspace_agent_record(
                workspace_id,
                record=record,
                configs=configs,
                defaults=defaults,
                companies=companies,
                staffing_template=staffing_template,
            )
        )

    for workspace_id, binding in bindings.items():
        if workspace_id in seen:
            continue
        legacy = configs.get(workspace_id)
        if legacy is not None and not legacy.enabled:
            continue
        record = {
            "workspace_id": workspace_id,
            "connection_kind": "project_path",
            "project_root": str(binding.project_root),
        }
        if binding.display_name:
            record["display_name"] = binding.display_name
        agents.append(
            build_workspace_agent_record(
                workspace_id,
                record=record,
                configs=configs,
                defaults=defaults,
                companies=companies,
                staffing_template=staffing_template,
            )
        )
        seen.add(workspace_id)

    agents.sort(key=lambda row: str(row.get("agent_name", "")).lower())
    return agents


def get_workspace_agent_record(workspace_id: str) -> dict[str, object]:
    normalized_id = workspace_id.strip()
    if not normalized_id:
        raise WorkspaceAgentError("workspace_id is required")
    try:
        record = get_workspace_record(normalized_id)
    except WorkspaceNotFoundError as exc:
        raise WorkspaceAgentError(str(exc)) from exc
    return build_workspace_agent_record(normalized_id, record=record)


def get_company_roster(workspace_id: str) -> dict[str, object]:
    normalized_id = workspace_id.strip()
    if not normalized_id:
        raise WorkspaceAgentError("workspace_id is required")
    try:
        record = get_workspace_record(normalized_id)
    except WorkspaceNotFoundError as exc:
        raise WorkspaceAgentError(str(exc)) from exc
    return {
        "company": build_company_roster(normalized_id, record=record),
        "role_catalog": list(ROLE_CATALOG),
    }


def list_role_catalog() -> list[dict[str, str]]:
    return list(ROLE_CATALOG)
