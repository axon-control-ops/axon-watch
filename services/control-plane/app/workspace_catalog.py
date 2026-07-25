"""Canonical workspace-record projection for the control-plane thin slice."""

from __future__ import annotations

from app.adapters.watch_client import fetch_watch_inbox
from app.inbox_projection import WatchInboxFetcher, build_inbox_response
from app.runs.service import list_runs
from app.operator_workspace_scope import filter_operator_workspace_records
from app.workspace_project_bindings import WorkspaceProjectBinding, load_workspace_project_bindings


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


def _workspace_record(
    workspace_id: str,
    binding: WorkspaceProjectBinding | None = None,
) -> dict[str, str]:
    record: dict[str, str] = {
        "workspace_id": workspace_id,
        "connection_kind": "project_path" if binding else "isolated_root",
    }
    if binding is not None:
        record["project_root"] = str(binding.project_root)
        if binding.display_name:
            record["display_name"] = binding.display_name
    return record


def list_workspace_records(
    *,
    inbox_fetcher: WatchInboxFetcher | None = None,
    operator_surface: bool = False,
) -> list[dict[str, str]]:
    bindings = load_workspace_project_bindings()
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

    records = [
        _workspace_record(workspace_id, bindings.get(workspace_id))
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
) -> dict[str, str]:
    bindings = load_workspace_project_bindings()
    normalized_id = workspace_id.strip()
    if normalized_id in bindings:
        return _workspace_record(normalized_id, bindings[normalized_id])

    for record in list_workspace_records(inbox_fetcher=inbox_fetcher):
        if record["workspace_id"] == normalized_id:
            return record
    raise WorkspaceNotFoundError(f"workspace not found: {workspace_id}")
