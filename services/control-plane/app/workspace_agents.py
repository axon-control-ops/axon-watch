"""Workspace company roster — each workspace is a company with role-based employees."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.runs.service import list_runs
from app.workspace_catalog import WorkspaceNotFoundError, get_workspace_record, list_workspace_records
from app.workspace_project_bindings import load_workspace_project_bindings


class WorkspaceAgentError(ValueError):
    pass


WORKSPACE_AGENT_STATUSES = (
    "idle",
    "watching",
    "planning",
    "executing",
    "verifying",
    "blocked",
    "waiting_approval",
    "handoff_ready",
)

EMPLOYEE_SCHEDULES = ("always_on", "continuous", "on_demand")

ROLE_CATALOG: tuple[dict[str, str], ...] = (
    {
        "id": "lead",
        "label": "Company Lead",
        "summary": "Owns priorities, handoffs, and final review",
        "default_schedule": "on_demand",
    },
    {
        "id": "watcher",
        "label": "Night Watch",
        "summary": "Monitors signals and runtime health around the clock",
        "default_schedule": "always_on",
    },
    {
        "id": "frontend",
        "label": "Frontend Engineer",
        "summary": "Owns UI/UX surfaces and shell polish",
        "default_schedule": "continuous",
    },
    {
        "id": "backend",
        "label": "Backend Engineer",
        "summary": "Owns APIs, control plane, and persistence",
        "default_schedule": "continuous",
    },
    {
        "id": "integrations",
        "label": "Integrations Engineer",
        "summary": "Owns connectors and cross-service wiring",
        "default_schedule": "continuous",
    },
    {
        "id": "workspace_agent",
        "label": "Workspace Agent",
        "summary": "General company employee for assigned workspace work",
        "default_schedule": "on_demand",
    },
    {
        "id": "overview_agent",
        "label": "Overview Agent",
        "summary": "Cross-workspace overview and routing",
        "default_schedule": "on_demand",
    },
)

_ROLE_BY_ID = {entry["id"]: entry for entry in ROLE_CATALOG}

_SCHEDULE_LABELS = {
    "always_on": "Always on (24/7)",
    "continuous": "Continuous",
    "on_demand": "On demand",
}

_DEFAULT_OWNS = {
    "lead": "priorities, handoffs, and product direction",
    "watcher": "signals, connectors, and runtime health",
    "frontend": "UI/UX, shell, and frontend polish",
    "backend": "APIs, control plane, and persistence",
    "integrations": "connectors and integrated services",
}

_BRAND_CASE = {
    "axon": "Axon",
    "dashpro": "DashPro",
}


@dataclass(frozen=True)
class EmployeeConfig:
    name: str | None = None
    role: str = "workspace_agent"
    owns: str = ""
    schedule: str = "on_demand"
    enabled: bool = True
    primary: bool = False
    employee_id: str | None = None


@dataclass(frozen=True)
class CompanyConfig:
    company_name: str | None = None
    employees: tuple[EmployeeConfig, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class WorkspaceAgentConfig:
    """Legacy single-agent override; still supported as a one-employee company."""

    agent_name: str | None = None
    role: str = "workspace_agent"
    owns: str = ""
    enabled: bool = True
    schedule: str = "on_demand"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_agents_file() -> Path:
    configured = os.environ.get("AXON_WATCH_WORKSPACE_AGENTS_FILE", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = (_repo_root() / path).resolve()
        return path
    return (_repo_root() / "config" / "workspace-agents.json").resolve()


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _title_display_name(value: str) -> str:
    raw = _clean_text(value)
    if not raw:
        return "Workspace"
    words = re.split(r"[\s_-]+", raw)
    titled = [_BRAND_CASE.get(word.lower(), word[:1].upper() + word[1:]) for word in words if word]
    return " ".join(titled) or "Workspace"


def _agent_key(workspace_id: str, display_name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", display_name.lower()).strip("_")
    if not base:
        base = workspace_id.replace("-", "_")
    return f"{base}_workspace_agent"


def _agent_id(workspace_id: str) -> str:
    return f"workspace-agent-{workspace_id}"


def _employee_id(workspace_id: str, role: str, index: int) -> str:
    role_slug = re.sub(r"[^a-z0-9]+", "-", role.lower()).strip("-") or "employee"
    return f"employee-{workspace_id}-{role_slug}-{index}"


def _normalize_schedule(value: Any, *, role: str) -> str:
    schedule = _clean_text(value).lower().replace("-", "_").replace(" ", "_")
    if schedule in EMPLOYEE_SCHEDULES:
        return schedule
    catalog = _ROLE_BY_ID.get(role)
    if catalog:
        return catalog["default_schedule"]
    return "on_demand"


def _normalize_role(value: Any) -> str:
    role = _clean_text(value).lower().replace("-", "_").replace(" ", "_")
    if not role:
        return "workspace_agent"
    aliases = {
        "ui": "frontend",
        "ux": "frontend",
        "ui_ux": "frontend",
        "front_end": "frontend",
        "back_end": "backend",
        "monitor": "watcher",
        "monitoring": "watcher",
        "night_watch": "watcher",
        "company_lead": "lead",
        "ceo": "lead",
    }
    return aliases.get(role, role)


def _role_label(role: str) -> str:
    catalog = _ROLE_BY_ID.get(role)
    if catalog:
        return catalog["label"]
    return _title_display_name(role.replace("_", " "))


def _schedule_label(schedule: str) -> str:
    return _SCHEDULE_LABELS.get(schedule, _title_display_name(schedule.replace("_", " ")))


def _parse_employee_config(raw: Any, *, default_primary: bool = False) -> EmployeeConfig | None:
    if not isinstance(raw, dict):
        return None
    role = _normalize_role(raw.get("role"))
    name = _clean_text(raw.get("name") or raw.get("agent_name")) or None
    owns = _clean_text(raw.get("owns"))
    schedule = _normalize_schedule(raw.get("schedule"), role=role)
    enabled = raw.get("enabled")
    enabled_value = True if enabled is None else bool(enabled)
    primary_raw = raw.get("primary")
    primary = default_primary if primary_raw is None else bool(primary_raw)
    employee_id = _clean_text(raw.get("employee_id") or raw.get("id")) or None
    return EmployeeConfig(
        name=name,
        role=role,
        owns=owns,
        schedule=schedule,
        enabled=enabled_value,
        primary=primary,
        employee_id=employee_id,
    )


def _parse_agent_config(raw: Any) -> WorkspaceAgentConfig | None:
    if not isinstance(raw, dict):
        return None
    agent_name = _clean_text(raw.get("agent_name") or raw.get("name")) or None
    role = _normalize_role(raw.get("role") or "workspace_agent")
    owns = _clean_text(raw.get("owns"))
    enabled = raw.get("enabled")
    enabled_value = True if enabled is None else bool(enabled)
    schedule = _normalize_schedule(raw.get("schedule"), role=role)
    return WorkspaceAgentConfig(
        agent_name=agent_name,
        role=role,
        owns=owns,
        enabled=enabled_value,
        schedule=schedule,
    )


def _default_staffing_template() -> list[dict[str, str]]:
    return [
        {"role": "lead", "schedule": "on_demand"},
        {"role": "watcher", "schedule": "always_on"},
        {"role": "frontend", "schedule": "continuous"},
        {"role": "backend", "schedule": "continuous"},
        {"role": "integrations", "schedule": "continuous"},
    ]


def load_workspace_agent_configs(
    agents_file: Path | None = None,
) -> tuple[
    dict[str, WorkspaceAgentConfig],
    dict[str, str],
    dict[str, CompanyConfig],
    list[dict[str, str]],
]:
    path = agents_file or default_agents_file()
    defaults = {
        "role": "workspace_agent",
        "name_template": "{display_name} Workspace Agent",
        "company_name_template": "{display_name}",
    }
    staffing_template = _default_staffing_template()
    if not path.is_file():
        return {}, defaults, {}, staffing_template

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceAgentError(f"unable to read workspace agents file: {path}") from exc

    raw_defaults = payload.get("defaults")
    if isinstance(raw_defaults, dict):
        defaults["role"] = _normalize_role(raw_defaults.get("role")) or defaults["role"]
        defaults["name_template"] = (
            _clean_text(raw_defaults.get("name_template")) or defaults["name_template"]
        )
        defaults["company_name_template"] = (
            _clean_text(raw_defaults.get("company_name_template"))
            or defaults["company_name_template"]
        )
        raw_template = raw_defaults.get("staffing_template")
        if isinstance(raw_template, list) and raw_template:
            parsed_template: list[dict[str, str]] = []
            for entry in raw_template:
                if not isinstance(entry, dict):
                    continue
                role = _normalize_role(entry.get("role"))
                parsed_template.append(
                    {
                        "role": role,
                        "schedule": _normalize_schedule(entry.get("schedule"), role=role),
                    }
                )
            if parsed_template:
                staffing_template = parsed_template

    configs: dict[str, WorkspaceAgentConfig] = {}
    raw_agents = payload.get("agents")
    if isinstance(raw_agents, dict):
        for workspace_id, entry in raw_agents.items():
            normalized_id = str(workspace_id).strip()
            if not normalized_id:
                continue
            parsed = _parse_agent_config(entry)
            if parsed is not None:
                configs[normalized_id] = parsed

    companies: dict[str, CompanyConfig] = {}
    raw_companies = payload.get("companies")
    if isinstance(raw_companies, dict):
        for workspace_id, entry in raw_companies.items():
            normalized_id = str(workspace_id).strip()
            if not normalized_id or not isinstance(entry, dict):
                continue
            company_name = _clean_text(entry.get("company_name") or entry.get("name")) or None
            employees: list[EmployeeConfig] = []
            raw_employees = entry.get("employees")
            if isinstance(raw_employees, list):
                for index, raw_employee in enumerate(raw_employees):
                    parsed_employee = _parse_employee_config(
                        raw_employee,
                        default_primary=index == 0,
                    )
                    if parsed_employee is not None:
                        employees.append(parsed_employee)
            companies[normalized_id] = CompanyConfig(
                company_name=company_name,
                employees=tuple(employees),
            )

    return configs, defaults, companies, staffing_template


def _display_name_for_workspace(workspace_id: str, record: dict[str, str]) -> str:
    display_name = _clean_text(record.get("display_name"))
    if display_name:
        return display_name
    suffix = workspace_id.removeprefix("workspace_").replace("_", " ").strip()
    return _title_display_name(suffix or workspace_id)


def _default_agent_name(display_name: str, *, name_template: str) -> str:
    template = name_template or "{display_name} Workspace Agent"
    return template.replace("{display_name}", _title_display_name(display_name))


def _default_company_name(display_name: str, *, company_name_template: str) -> str:
    template = company_name_template or "{display_name}"
    return template.replace("{display_name}", _title_display_name(display_name))


def _default_employee_name(display_name: str, role: str) -> str:
    company = _title_display_name(display_name)
    if role == "lead":
        return f"{company} Lead"
    if role == "watcher":
        return f"{company} Night Watch"
    if role == "frontend":
        return f"{company} Frontend"
    if role == "backend":
        return f"{company} Backend"
    if role == "integrations":
        return f"{company} Integrations"
    return f"{company} {_role_label(role)}"


def _derive_agent_status(workspace_id: str) -> str:
    active_statuses = {
        "running",
        "waiting",
        "blocked",
        "review",
        # Legacy values retained for older persisted runs.
        "paused",
        "review_ready",
    }
    workspace_runs = [
        run
        for run in list_runs()
        if str(run.get("workspace_id", "")).strip() == workspace_id.strip()
        and not run.get("ended_at")
    ]
    runs = [
        run
        for run in workspace_runs
        if str(run.get("status", "")).strip() in active_statuses
    ]
    if not runs:
        return "idle"

    runs.sort(key=lambda run: str(run.get("updated_at") or run.get("started_at") or ""), reverse=True)
    primary = runs[0]
    phase = str(primary.get("phase", "")).strip()
    status = str(primary.get("status", "")).strip()

    if phase == "awaiting_approval":
        derived = "waiting_approval"
    elif phase == "planning" or str(primary.get("mode", "")).strip() == "plan":
        derived = "planning"
    elif status in {"review", "review_ready"} or phase == "review_ready":
        derived = "verifying"
    elif status == "blocked" or phase in {"paused", "awaiting_input"}:
        derived = "blocked"
    elif phase == "executing" or status == "running":
        derived = "executing"
    else:
        derived = "watching"
    return derived


def _employee_status(*, role: str, schedule: str, workspace_status: str, primary: bool) -> str:
    if primary or role in {"lead", "workspace_agent", "overview_agent"}:
        if workspace_status != "idle":
            return workspace_status
        if schedule == "always_on" or role == "watcher":
            return "watching"
        return "idle"

    # Shared company blockers surface for everyone.
    if workspace_status in {"blocked", "waiting_approval"}:
        return workspace_status

    # Always-on watchers stay on duty even when no run is active.
    if schedule == "always_on" or role == "watcher":
        return "watching"

    # Role specialists stay idle until role-tagged runs exist.
    return "idle"


def _resolve_employees(
    workspace_id: str,
    *,
    display_name: str,
    company: CompanyConfig | None,
    legacy: WorkspaceAgentConfig | None,
    defaults: dict[str, str],
    staffing_template: list[dict[str, str]],
) -> list[EmployeeConfig]:
    if company is not None and company.employees:
        employees = list(company.employees)
        if not any(employee.primary for employee in employees):
            first = employees[0]
            employees[0] = EmployeeConfig(
                name=first.name,
                role=first.role,
                owns=first.owns,
                schedule=first.schedule,
                enabled=first.enabled,
                primary=True,
                employee_id=first.employee_id,
            )
        return employees

    if legacy is not None:
        return [
            EmployeeConfig(
                name=legacy.agent_name,
                role=legacy.role or defaults.get("role", "workspace_agent"),
                owns=legacy.owns,
                schedule=legacy.schedule,
                enabled=legacy.enabled,
                primary=True,
            )
        ]

    employees: list[EmployeeConfig] = []
    for index, entry in enumerate(staffing_template):
        role = _normalize_role(entry.get("role"))
        schedule = _normalize_schedule(entry.get("schedule"), role=role)
        employees.append(
            EmployeeConfig(
                name=_default_employee_name(display_name, role),
                role=role,
                owns=_DEFAULT_OWNS.get(role, f"{_title_display_name(display_name)} assigned work"),
                schedule=schedule,
                enabled=True,
                primary=index == 0 or role == "lead",
            )
        )
    if employees and not any(employee.primary for employee in employees):
        first = employees[0]
        employees[0] = EmployeeConfig(
            name=first.name,
            role=first.role,
            owns=first.owns,
            schedule=first.schedule,
            enabled=first.enabled,
            primary=True,
            employee_id=first.employee_id,
        )
    # Ensure only one primary.
    primary_seen = False
    normalized: list[EmployeeConfig] = []
    for employee in employees:
        is_primary = employee.primary and not primary_seen
        if is_primary:
            primary_seen = True
        normalized.append(
            EmployeeConfig(
                name=employee.name,
                role=employee.role,
                owns=employee.owns,
                schedule=employee.schedule,
                enabled=employee.enabled,
                primary=is_primary,
                employee_id=employee.employee_id,
            )
        )
    return normalized


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
    workspace_status = _derive_agent_status(normalized_id)
    employee_rows: list[dict[str, object]] = []
    primary_employee_id: str | None = None

    for index, employee in enumerate(employees):
        if not employee.enabled:
            continue
        role = employee.role or "workspace_agent"
        schedule = employee.schedule or _normalize_schedule(None, role=role)
        emp_id = employee.employee_id or _employee_id(normalized_id, role, index)
        name = employee.name or _default_employee_name(display_name, role)
        owns = employee.owns or _DEFAULT_OWNS.get(
            role,
            f"{_title_display_name(display_name)} assigned work only",
        )
        status = _employee_status(
            role=role,
            schedule=schedule,
            workspace_status=workspace_status,
            primary=employee.primary,
        )
        if employee.primary:
            primary_employee_id = emp_id
        employee_rows.append(
            {
                "employee_id": emp_id,
                "workspace_id": normalized_id,
                "name": name,
                "role": role,
                "role_label": _role_label(role),
                "schedule": schedule,
                "schedule_label": _schedule_label(schedule),
                "status": status,
                "owns": owns,
                "enabled": True,
                "primary": employee.primary,
            }
        )

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
            "status": _derive_agent_status(normalized_id),
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
            "status": primary.get("status") or _derive_agent_status(normalized_id),
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
