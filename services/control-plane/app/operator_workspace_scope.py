"""Filter demo/isolated workspaces from operator-facing surfaces."""

from __future__ import annotations

# Legacy mockup / acceptance-test workspaces — hidden from operator fleet/brain/catalog
# when scope=operator. Still reachable by id for TEST-0 and parity suites.
DEMO_ISOLATED_WORKSPACE_IDS = frozenset(
    {
        "workspace_smoke",
        "workspace_recsys",
        "workspace_finance",
        "workspace_nlp",
        "workspace_cv",
        "workspace_edge",
        "workspace_research",
        "workspace_alpha",
        "workspace_bootstrap",
    }
)


def is_demo_isolated_workspace(workspace_id: str) -> bool:
    return workspace_id.strip() in DEMO_ISOLATED_WORKSPACE_IDS


def is_operator_surface_workspace(
    record: dict[str, str],
    *,
    bound_workspace_ids: frozenset[str] | set[str] | None = None,
) -> bool:
    """True when a workspace should appear on operator fleet/brain/catalog surfaces."""
    workspace_id = str(record.get("workspace_id", "")).strip()
    if not workspace_id:
        return False

    if bound_workspace_ids and workspace_id in bound_workspace_ids:
        return True

    if record.get("connection_kind") == "project_path":
        return True

    return not is_demo_isolated_workspace(workspace_id)


def filter_operator_workspace_records(
    records: list[dict[str, str]],
    *,
    bound_workspace_ids: frozenset[str] | set[str] | None = None,
) -> list[dict[str, str]]:
    return [
        record
        for record in records
        if is_operator_surface_workspace(record, bound_workspace_ids=bound_workspace_ids)
    ]
