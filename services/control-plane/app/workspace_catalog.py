"""Canonical workspace-record projection for the control-plane thin slice."""

from __future__ import annotations

from app.inbox_projection import WatchInboxFetcher, build_inbox_response
from app.runs.service import list_runs

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


def _workspace_record(workspace_id: str) -> dict[str, str]:
    return {"workspace_id": workspace_id}


def list_workspace_records(
    *,
    inbox_fetcher: WatchInboxFetcher | None = None,
) -> list[dict[str, str]]:
    workspace_ids = {
        str(record.get("workspace_id", "")).strip()
        for record in list_runs()
        if str(record.get("workspace_id", "")).strip()
    }
    workspace_ids.update(_OPERATOR_WORKSPACE_IDS)
    workspace_ids.update(_DEFAULT_WORKSPACE_IDS)

    inbox_snapshot = build_inbox_response(inbox_fetcher=inbox_fetcher)
    for item in inbox_snapshot.get("items", []):
        if isinstance(item, dict):
            workspace_id = str(item.get("workspace_id", "")).strip()
            if workspace_id:
                workspace_ids.add(workspace_id)

    return [_workspace_record(workspace_id) for workspace_id in sorted(workspace_ids)]


def get_workspace_record(
    workspace_id: str,
    *,
    inbox_fetcher: WatchInboxFetcher | None = None,
) -> dict[str, str]:
    for record in list_workspace_records(inbox_fetcher=inbox_fetcher):
        if record["workspace_id"] == workspace_id:
            return record
    raise WorkspaceNotFoundError(f"workspace not found: {workspace_id}")
