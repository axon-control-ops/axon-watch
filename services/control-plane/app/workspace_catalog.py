"""Canonical workspace-record projection for the control-plane thin slice."""

from __future__ import annotations

from app.adapters.watch_client import fetch_watch_inbox
from app.inbox_projection import WatchInboxFetcher, build_inbox_response
from app.runs.service import list_runs
from app.operator_workspace_scope import filter_operator_workspace_records
from app.workspace_project_bindings import (
    WorkspaceProjectBinding,
    get_workspace_project_binding,
    list_valid_workspace_project_bindings,
)


def _catalog_inbox_fetcher() -> dict[str, object] | None:
    """Never block agent/workspace lists on a cold watch inbox probe."""
    return fetch_watch_inbox(cached_only=True)

_OPERATOR_WORKSPACE_IDS = (
    "workspace_smoke",
    "workspace_recsys",
    "workspace_finance",
    "workspace_nlp",
    "workspace_cv",
    "workspace_edge",
    "workspace_research",
)

_DEFAULT_WORKSPACE_IDS = ("workspace_alpha", "workspace_bootstrap")


class WorkspaceNotFoundError(ValueError):
    pass


def _staffed_workspace_ids() -> frozenset[str]:
    """Workspaces with a configured company that has at least one enabled
    employee — i.e. a team someone could actually be talking to right now."""
    from app.workspace_agents.config_loader import load_workspace_agent_configs

    _configs, _defaults, companies, _staffing = load_workspace_agent_configs()
    return frozenset(
        workspace_id
        for workspace_id, company in companies.items()
        if any(employee.enabled for employee in company.employees)
    )


def _workspace_auto_enabled(workspace_id: str) -> bool | None:
    """Whether the operator has switched AUTO dispatch on for this workspace.

    The workspace picker is an operator surface, so "on/off" should follow the
    same per-workspace AUTO toggle used by Mission Control instead of inferring
    activity from whether a hand-authored company roster exists.
    """
    try:
        from app.persistence.workspace_composer_prefs_store import get_workspace_composer_prefs

        prefs = get_workspace_composer_prefs(workspace_id)
    except Exception:  # noqa: BLE001 - catalog listings must remain best-effort
        return None
    allowed = prefs.get("auto_allowed_runtimes")
    return isinstance(allowed, list) and any(isinstance(item, str) and item.strip() for item in allowed)


def _workspace_record(
    workspace_id: str,
    binding: WorkspaceProjectBinding | None = None,
    *,
    staffed_ids: frozenset[str] | None = None,
) -> dict[str, str | bool]:
    staffed = staffed_ids if staffed_ids is not None else _staffed_workspace_ids()
    auto_enabled = _workspace_auto_enabled(workspace_id)
    record: dict[str, str | bool] = {
        "workspace_id": workspace_id,
        "connection_kind": "project_path" if binding else "isolated_root",
        "has_active_team": workspace_id in staffed,
    }
    if auto_enabled is not None:
        record["auto_enabled"] = auto_enabled
    if binding is not None:
        record["project_root"] = str(binding.project_root)
        if binding.display_name:
            record["display_name"] = binding.display_name
    return record


def list_workspace_records(
    *,
    inbox_fetcher: WatchInboxFetcher | None = None,
    operator_surface: bool = False,
) -> list[dict[str, str | bool]]:
    # Best-effort: a misconfigured, unrelated workspace binding must not take
    # the entire /api/workspaces listing down for every other workspace.
    bindings = list_valid_workspace_project_bindings()
    workspace_ids = {
        str(record.get("workspace_id", "")).strip()
        for record in list_runs()
        if str(record.get("workspace_id", "")).strip()
    }
    if not operator_surface:
        workspace_ids.update(_OPERATOR_WORKSPACE_IDS)
        workspace_ids.update(_DEFAULT_WORKSPACE_IDS)
    workspace_ids.update(bindings.keys())

    inbox_snapshot = build_inbox_response(
        inbox_fetcher=inbox_fetcher or _catalog_inbox_fetcher,
        allow_empty_unavailable=True,
    )
    for item in inbox_snapshot.get("items", []):
        if isinstance(item, dict):
            workspace_id = str(item.get("workspace_id", "")).strip()
            if workspace_id:
                workspace_ids.add(workspace_id)

    staffed_ids = _staffed_workspace_ids()
    records = [
        _workspace_record(workspace_id, bindings.get(workspace_id), staffed_ids=staffed_ids)
        for workspace_id in sorted(workspace_ids)
    ]
    if not operator_surface:
        return records

    return filter_operator_workspace_records(
        records,
        bound_workspace_ids=frozenset(bindings.keys()),
    )


def get_workspace_record(
    workspace_id: str,
    *,
    inbox_fetcher: WatchInboxFetcher | None = None,
) -> dict[str, str | bool]:
    normalized_id = workspace_id.strip()
    # Resolve only this workspace's own binding, not the full registry: an
    # unrelated workspace's project_root moving outside the allowlist used to
    # break every other workspace's lookup here, since the full-registry
    # loader fails closed for the whole map when any one entry is invalid.
    binding = get_workspace_project_binding(normalized_id)
    if binding is not None:
        return _workspace_record(normalized_id, binding)

    for record in list_workspace_records(inbox_fetcher=inbox_fetcher):
        if record["workspace_id"] == normalized_id:
            return record
    raise WorkspaceNotFoundError(f"workspace not found: {workspace_id}")
