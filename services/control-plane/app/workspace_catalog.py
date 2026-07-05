"""Canonical workspace-record projection for the control-plane thin slice."""

from __future__ import annotations

from app.inbox_projection import WatchInboxFetcher, build_inbox_response
from app.runs.service import list_runs
from app.workspace_project_bindings import WorkspaceProjectBinding, load_workspace_project_bindings

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
) -> list[dict[str, str]]:
    bindings = load_workspace_project_bindings()
    workspace_ids = {
        str(record.get("workspace_id", "")).strip()
        for record in list_runs()
        if str(record.get("workspace_id", "")).strip()
    }
    workspace_ids.update(_OPERATOR_WORKSPACE_IDS)
    workspace_ids.update(_DEFAULT_WORKSPACE_IDS)
    workspace_ids.update(bindings.keys())

    inbox_snapshot = build_inbox_response(inbox_fetcher=inbox_fetcher)
    for item in inbox_snapshot.get("items", []):
        if isinstance(item, dict):
            workspace_id = str(item.get("workspace_id", "")).strip()
            if workspace_id:
                workspace_ids.add(workspace_id)

    return [
        _workspace_record(workspace_id, bindings.get(workspace_id))
        for workspace_id in sorted(workspace_ids)
    ]


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
