"""Operator bridge: connect fleet workspaces to DashPro Supabase and sibling services.

Humans run live checks from a bound project root with a local ``.env``. Agent
sandboxes hide ``.env`` and block network by default. This module resolves a
whitelist of service keys from the operator project ``.env`` plus unlocked vault
fallbacks, injects them into sandbox subprocess env, and widens approved live
verify commands per workspace — without exposing secret values in receipts.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.cli_runtime.vault_keys import runtime_vault_env
from app.workspace_project_bindings import (
    get_workspace_project_binding,
    list_valid_workspace_project_bindings,
)


class WorkspaceServiceConnectionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class WorkspaceServiceConnection:
    workspace_id: str
    display_name: str | None
    product: str
    dashpro_tenant_id: str | None
    env_keys: tuple[str, ...]
    required_services: tuple[str, ...]
    live_verify_command_prefixes: tuple[tuple[str, ...], ...]
    live_roles: frozenset[str]
    network_mode_for_live_roles: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_connections_file() -> Path:
    configured = os.environ.get("AXON_WATCH_WORKSPACE_SERVICE_CONNECTIONS_FILE", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = (_repo_root() / path).resolve()
        return path
    return (_repo_root() / "config" / "workspace-service-connections.json").resolve()


def _normalize_prefix(raw: object) -> tuple[str, ...] | None:
    if not isinstance(raw, list) or not raw:
        return None
    tokens = tuple(str(item).strip() for item in raw if str(item).strip())
    return tokens or None


def _parse_connection(workspace_id: str, entry: dict[str, Any]) -> WorkspaceServiceConnection:
    env_keys = tuple(
        dict.fromkeys(
            str(key).strip()
            for key in (entry.get("env_keys") or [])
            if str(key).strip()
        )
    )
    prefixes: list[tuple[str, ...]] = []
    for raw_prefix in entry.get("live_verify_command_prefixes") or []:
        normalized = _normalize_prefix(raw_prefix)
        if normalized:
            prefixes.append(normalized)
    live_roles = frozenset(
        str(role).strip().lower()
        for role in (entry.get("live_roles") or ("backend", "integrations", "watcher"))
        if str(role).strip()
    )
    required_services = tuple(
        dict.fromkeys(
            str(service).strip().lower()
            for service in (entry.get("required_services") or [])
            if str(service).strip()
        )
    )
    if not required_services:
        lowered_keys = {key.lower() for key in env_keys}
        inferred: list[str] = []
        if any("supabase" in key for key in lowered_keys):
            inferred.append("supabase")
        if any(key in {"github_token", "gh_token"} for key in lowered_keys):
            inferred.append("github")
        if any(key.startswith("sentry_") for key in lowered_keys):
            inferred.append("sentry")
        required_services = tuple(inferred)
    network_mode = str(entry.get("network_mode_for_live_roles") or "audited").strip().lower()
    if network_mode not in {"audited", "unrestricted"}:
        network_mode = "audited"
    tenant_raw = entry.get("dashpro_tenant_id")
    tenant_id = str(tenant_raw).strip() if tenant_raw not in (None, "") else None
    return WorkspaceServiceConnection(
        workspace_id=workspace_id,
        display_name=str(entry.get("display_name") or "").strip() or None,
        product=str(entry.get("product") or "edudash").strip(),
        dashpro_tenant_id=tenant_id,
        env_keys=env_keys,
        required_services=required_services,
        live_verify_command_prefixes=tuple(prefixes),
        live_roles=live_roles,
        network_mode_for_live_roles=network_mode,
    )


def load_workspace_service_connections(
    connections_file: Path | None = None,
) -> dict[str, WorkspaceServiceConnection]:
    path = connections_file or default_connections_file()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceServiceConnectionError(f"unable to read connections file: {path}") from exc
    entries = payload.get("connections")
    if not isinstance(entries, dict):
        raise WorkspaceServiceConnectionError("connections file must contain a connections object")
    connections: dict[str, WorkspaceServiceConnection] = {}
    for workspace_id, entry in entries.items():
        normalized_id = str(workspace_id).strip()
        if not normalized_id or not isinstance(entry, dict):
            continue
        connections[normalized_id] = _parse_connection(normalized_id, entry)
    return connections


def get_workspace_service_connection(workspace_id: str) -> WorkspaceServiceConnection | None:
    normalized = str(workspace_id or "").strip()
    if not normalized:
        return None
    return load_workspace_service_connections().get(normalized)


def workspace_id_for_project_root(project_root: Path | str) -> str | None:
    candidate = Path(project_root).expanduser().resolve()
    for workspace_id, binding in list_valid_workspace_project_bindings().items():
        if binding.project_root.resolve() == candidate:
            return workspace_id
    return None


def parse_operator_dotenv(project_root: Path, allowed_keys: tuple[str, ...]) -> dict[str, str]:
    """Read only whitelisted keys from the operator-maintained project ``.env``."""
    if not allowed_keys:
        return {}
    env_path = project_root / ".env"
    if not env_path.is_file():
        return {}
    allowed = frozenset(allowed_keys)
    resolved: dict[str, str] = {}
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    for line in lines:
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#") or "=" not in trimmed:
            continue
        index = trimmed.index("=")
        key = trimmed[:index].strip()
        if key not in allowed:
            continue
        value = trimmed[index + 1 :].strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        if value:
            resolved[key] = value
    return resolved


def resolve_workspace_live_env(
    workspace_id: str,
    *,
    include_vault: bool = True,
) -> dict[str, str]:
    """Merge operator project ``.env`` with vault fallbacks for configured keys."""
    connection = get_workspace_service_connection(workspace_id)
    if connection is None or not connection.env_keys:
        return {}
    binding = get_workspace_project_binding(workspace_id)
    if binding is None:
        return {}
    merged = parse_operator_dotenv(binding.project_root, connection.env_keys)
    if include_vault:
        vault_env = runtime_vault_env()
        for key in connection.env_keys:
            if key not in merged:
                value = str(vault_env.get(key) or "").strip()
                if value:
                    merged[key] = value
    return merged


def live_verify_prefixes_for_workspace(workspace_id: str) -> tuple[tuple[str, ...], ...]:
    connection = get_workspace_service_connection(workspace_id)
    if connection is None:
        return ()
    return connection.live_verify_command_prefixes


def apply_live_service_policy(
    policy: Any,
    *,
    workspace_id: str,
    role: str,
) -> Any:
    """Widen command prefixes and network for configured live-service workspaces."""
    from dataclasses import replace

    approved_prefixes = getattr(policy, "approved_command_prefixes", None)
    policy_network_mode = getattr(policy, "network_mode", None)
    if approved_prefixes is None or policy_network_mode is None:
        return policy
    connection = get_workspace_service_connection(workspace_id)
    if connection is None:
        return policy
    normalized_role = str(role or "").strip().lower()
    if normalized_role not in connection.live_roles:
        return policy
    extra_prefixes = connection.live_verify_command_prefixes
    if not extra_prefixes and policy_network_mode != "none":
        return policy
    merged_prefixes = tuple(
        dict.fromkeys((*approved_prefixes, *extra_prefixes))
    )
    network_mode = policy_network_mode
    if policy_network_mode == "none" and extra_prefixes:
        network_mode = connection.network_mode_for_live_roles
    if merged_prefixes == approved_prefixes and network_mode == policy_network_mode:
        return policy
    return replace(
        policy,
        approved_command_prefixes=merged_prefixes,
        network_mode=network_mode,
    )


def workspace_service_connection_posture(workspace_id: str) -> dict[str, object]:
    """Operator-safe readiness snapshot — never includes secret values."""
    connection = get_workspace_service_connection(workspace_id)
    binding = get_workspace_project_binding(workspace_id)
    if connection is None:
        return {
            "workspace_id": workspace_id,
            "configured": False,
            "ready": False,
            "hint": "No service connection profile for this workspace.",
        }
    project_root = str(binding.project_root) if binding else ""
    dotenv_path = str(binding.project_root / ".env") if binding else ""
    dotenv_present = binding is not None and (binding.project_root / ".env").is_file()
    resolved = resolve_workspace_live_env(workspace_id)
    key_status = {
        key: key in resolved
        for key in connection.env_keys
    }
    service_key_predicates = {
        "github": lambda key: key in {"GITHUB_TOKEN", "GH_TOKEN"},
        "sentry": lambda key: key.startswith("SENTRY_"),
        "supabase": lambda key: "SUPABASE" in key,
    }
    service_status = {
        service: any(
            resolved.get(key)
            for key in connection.env_keys
            if service_key_predicates.get(service, lambda _key: False)(key)
        )
        for service in connection.required_services
    }
    services_ready = all(service_status.values()) if service_status else True
    ready = dotenv_present and services_ready
    hint = "Live service bridge ready — fleet may run configured verify commands."
    if not binding:
        ready = False
        hint = "Bind a project_root in workspace-project-bindings.json first."
    elif not dotenv_present:
        ready = False
        hint = "Materialize operator .env from .env.example on the bound project root."
    elif not services_ready:
        ready = False
        missing = ", ".join(service for service, ok in service_status.items() if not ok)
        hint = f"Add {missing} keys to operator .env or unlock /vault with matching keys."
    return {
        "workspace_id": workspace_id,
        "configured": True,
        "ready": ready,
        "display_name": connection.display_name,
        "product": connection.product,
        "dashpro_tenant_id": connection.dashpro_tenant_id,
        "project_root": project_root,
        "operator_dotenv_path": dotenv_path,
        "operator_dotenv_present": dotenv_present,
        "env_keys": list(connection.env_keys),
        "env_keys_resolved": key_status,
        "required_services": list(connection.required_services),
        "services_resolved": service_status,
        "live_verify_commands": [list(prefix) for prefix in connection.live_verify_command_prefixes],
        "live_roles": sorted(connection.live_roles),
        "network_mode_for_live_roles": connection.network_mode_for_live_roles,
        "hint": hint,
    }


__all__ = [
    "WorkspaceServiceConnection",
    "WorkspaceServiceConnectionError",
    "apply_live_service_policy",
    "default_connections_file",
    "get_workspace_service_connection",
    "live_verify_prefixes_for_workspace",
    "load_workspace_service_connections",
    "parse_operator_dotenv",
    "resolve_workspace_live_env",
    "workspace_id_for_project_root",
    "workspace_service_connection_posture",
]
