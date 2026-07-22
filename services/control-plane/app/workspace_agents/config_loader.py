"""Load workspace agent company configuration from JSON."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.workspace_agents.catalog import (
    EMPLOYEE_SCHEDULES,
    ROLE_CATALOG,
    _BRAND_CASE,
    _DEFAULT_OWNS,
    _DEFAULT_ROLE_NAMES,
    _ROLE_BY_ID,
    _SCHEDULE_LABELS,
    scoped_default_owns,
    stable_role_persona,
)


class WorkspaceAgentError(ValueError):
    pass


@dataclass(frozen=True)
class EmployeeConfig:
    name: str | None = None
    role: str = "workspace_agent"
    owns: str = ""
    schedule: str = "on_demand"
    enabled: bool = True
    primary: bool = False
    employee_id: str | None = None
    azure_voice_id: str | None = None


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
    # config_loader.py lives at services/control-plane/app/workspace_agents/
    # → parents[4] is the repo root. parents[3] incorrectly resolves to services/
    # and makes default_agents_file miss config/workspace-agents.json.
    return Path(__file__).resolve().parents[4]


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
    azure_voice_id = _clean_text(
        raw.get("azure_voice_id") or raw.get("azureVoiceId") or raw.get("voice_id")
    ) or None
    return EmployeeConfig(
        name=name,
        role=role,
        owns=owns,
        schedule=schedule,
        enabled=enabled_value,
        primary=primary,
        employee_id=employee_id,
        azure_voice_id=azure_voice_id,
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


def _default_employee_name(workspace_id: str, display_name: str, role: str) -> str:
    del display_name  # Names are personal; company prefix is no longer used.
    name, _voice = stable_role_persona(workspace_id, role)
    return name


def _default_employee_voice(workspace_id: str, role: str) -> str | None:
    _name, voice = stable_role_persona(workspace_id, role)
    return voice


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
                azure_voice_id=first.azure_voice_id,
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
                name=_default_employee_name(workspace_id, display_name, role),
                role=role,
                owns=scoped_default_owns(display_name, role),
                schedule=schedule,
                enabled=True,
                primary=index == 0 or role == "lead",
                azure_voice_id=_default_employee_voice(workspace_id, role),
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
            azure_voice_id=first.azure_voice_id,
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
                azure_voice_id=employee.azure_voice_id,
            )
        )
    return normalized
