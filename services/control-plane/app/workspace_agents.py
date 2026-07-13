"""Workspace agent registry — named agents that workspaces employ."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
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

_BRAND_CASE = {
    "axon": "Axon",
    "dashpro": "DashPro",
}


@dataclass(frozen=True)
class WorkspaceAgentConfig:
    agent_name: str | None = None
    role: str = "workspace_agent"
    owns: str = ""
    enabled: bool = True


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


def _parse_agent_config(raw: Any) -> WorkspaceAgentConfig | None:
    if not isinstance(raw, dict):
        return None
    agent_name = _clean_text(raw.get("agent_name") or raw.get("name")) or None
    role = _clean_text(raw.get("role")) or "workspace_agent"
    owns = _clean_text(raw.get("owns"))
    enabled = raw.get("enabled")
    if enabled is None:
        enabled_value = True
    else:
        enabled_value = bool(enabled)
    return WorkspaceAgentConfig(
        agent_name=agent_name,
        role=role,
        owns=owns,
        enabled=enabled_value,
    )


def load_workspace_agent_configs(
    agents_file: Path | None = None,
) -> tuple[dict[str, WorkspaceAgentConfig], dict[str, str]]:
    path = agents_file or default_agents_file()
    defaults = {
        "role": "workspace_agent",
        "name_template": "{display_name} Workspace Agent",
    }
    if not path.is_file():
        return {}, defaults

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceAgentError(f"unable to read workspace agents file: {path}") from exc

    raw_defaults = payload.get("defaults")
    if isinstance(raw_defaults, dict):
        defaults["role"] = _clean_text(raw_defaults.get("role")) or defaults["role"]
        defaults["name_template"] = (
            _clean_text(raw_defaults.get("name_template")) or defaults["name_template"]
        )

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
    return configs, defaults


def _display_name_for_workspace(workspace_id: str, record: dict[str, str]) -> str:
    display_name = _clean_text(record.get("display_name"))
    if display_name:
        return display_name
    suffix = workspace_id.removeprefix("workspace_").replace("_", " ").strip()
    return _title_display_name(suffix or workspace_id)


def _default_agent_name(display_name: str, *, name_template: str) -> str:
    template = name_template or "{display_name} Workspace Agent"
    return template.replace("{display_name}", _title_display_name(display_name))


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
    # #region agent log
    try:
        from app.debug_session_log import append_debug_session_log

        excluded = [
            {
                "run_id": run.get("run_id"),
                "status": run.get("status"),
                "phase": run.get("phase"),
                "in_active_filter": str(run.get("status", "")).strip() in active_statuses,
            }
            for run in workspace_runs
        ]
        append_debug_session_log(
            hypothesis_id="EA1",
            location="workspace_agents.py:_derive_agent_status",
            message="employee agent status derivation",
            data={
                "workspace_id": workspace_id,
                "active_status_filter": sorted(active_statuses),
                "open_run_count": len(workspace_runs),
                "matched_run_count": len(runs),
                "open_runs": excluded[:8],
                "filter_excludes_review_status": any(
                    str(item.get("status") or "") == "review"
                    and not item.get("in_active_filter")
                    for item in excluded
                ),
            },
        )
    except Exception:
        pass
    # #endregion
    if not runs:
        # #region agent log
        try:
            from app.debug_session_log import append_debug_session_log

            append_debug_session_log(
                hypothesis_id="EA1",
                location="workspace_agents.py:_derive_agent_status:idle",
                message="employee agent marked idle — no runs matched active status filter",
                data={
                    "workspace_id": workspace_id,
                    "open_run_count": len(workspace_runs),
                    "open_run_statuses": [str(run.get("status") or "") for run in workspace_runs[:8]],
                    "open_run_phases": [str(run.get("phase") or "") for run in workspace_runs[:8]],
                },
            )
        except Exception:
            pass
        # #endregion
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
    # #region agent log
    try:
        from app.debug_session_log import append_debug_session_log

        append_debug_session_log(
            hypothesis_id="EA2",
            location="workspace_agents.py:_derive_agent_status:mapped",
            message="employee agent status mapped from primary run",
            data={
                "workspace_id": workspace_id,
                "derived": derived,
                "primary_run_id": primary.get("run_id"),
                "primary_status": status,
                "primary_phase": phase,
                "status_equals_review_ready_literal": status == "review_ready",
                "status_equals_review": status == "review",
            },
        )
    except Exception:
        pass
    # #endregion
    return derived


def build_workspace_agent_record(
    workspace_id: str,
    *,
    record: dict[str, str] | None = None,
    configs: dict[str, WorkspaceAgentConfig] | None = None,
    defaults: dict[str, str] | None = None,
) -> dict[str, object]:
    workspace_record = record or get_workspace_record(workspace_id)
    normalized_id = workspace_id.strip()
    config_map, default_values = (
        (configs, defaults)
        if configs is not None and defaults is not None
        else load_workspace_agent_configs()
    )
    config = config_map.get(normalized_id, WorkspaceAgentConfig())
    display_name = _display_name_for_workspace(normalized_id, workspace_record)
    agent_name = config.agent_name or _default_agent_name(
        display_name,
        name_template=default_values["name_template"],
    )

    payload: dict[str, object] = {
        "agent_id": _agent_id(normalized_id),
        "workspace_id": normalized_id,
        "agent_name": agent_name,
        "agent_key": _agent_key(normalized_id, display_name),
        "role": config.role or default_values["role"],
        "status": _derive_agent_status(normalized_id),
        "owns": config.owns or f"{display_name} assigned work only",
        "enabled": config.enabled,
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
    configs, defaults = load_workspace_agent_configs()
    workspace_records = list_workspace_records(operator_surface=operator_surface)
    bindings = load_workspace_project_bindings()

    agents: list[dict[str, object]] = []
    seen: set[str] = set()
    for record in workspace_records:
        workspace_id = str(record.get("workspace_id", "")).strip()
        if not workspace_id or workspace_id in seen:
            continue
        seen.add(workspace_id)
        config = configs.get(workspace_id)
        if config is not None and not config.enabled:
            continue
        agents.append(
            build_workspace_agent_record(
                workspace_id,
                record=record,
                configs=configs,
                defaults=defaults,
            )
        )

    for workspace_id, binding in bindings.items():
        if workspace_id in seen:
            continue
        config = configs.get(workspace_id)
        if config is not None and not config.enabled:
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
