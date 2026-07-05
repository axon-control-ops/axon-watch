"""Cross-workspace handoff orchestration for the control-plane thin slice."""

from __future__ import annotations

from app.persistence import handoff_store
from app.runs.service import list_runs
from app.workspace_catalog import WorkspaceNotFoundError, get_workspace_record


class WorkspaceHandoffError(ValueError):
    pass


def build_target_workspace_summary(workspace_id: str) -> dict[str, object]:
    record = get_workspace_record(workspace_id)
    runs = [
        run
        for run in list_runs()
        if str(run.get("workspace_id", "")).strip() == workspace_id.strip()
    ]
    active_runs = [
        {
            "run_id": run["run_id"],
            "status": run["status"],
            "phase": run["phase"],
            "summary": run["summary"],
        }
        for run in runs
        if str(run.get("status", "")).strip() in {"running", "paused", "review_ready"}
    ]

    return {
        **record,
        "run_count": len(runs),
        "active_run_count": len(active_runs),
        "active_runs": active_runs[:5],
    }


def create_workspace_handoff(
    *,
    source_workspace_id: str,
    target_workspace_id: str,
    task: str,
    reason: str = "",
) -> dict[str, object]:
    source_id = source_workspace_id.strip()
    target_id = target_workspace_id.strip()
    task_text = task.strip()

    if not source_id:
        raise WorkspaceHandoffError("source workspace_id is required")
    if not target_id:
        raise WorkspaceHandoffError("target_workspace_id is required")
    if not task_text:
        raise WorkspaceHandoffError("task is required")
    if source_id == target_id:
        raise WorkspaceHandoffError("target workspace must differ from source workspace")

    try:
        get_workspace_record(source_id)
        get_workspace_record(target_id)
    except WorkspaceNotFoundError as exc:
        raise WorkspaceHandoffError(str(exc)) from exc

    handoff = handoff_store.create_handoff_record(
        source_workspace_id=source_id,
        target_workspace_id=target_id,
        task=task_text,
        reason=reason,
    )
    target_workspace = get_workspace_record(target_id)
    target_workspace_summary = build_target_workspace_summary(target_id)

    return {
        "handoff": handoff,
        "target_workspace": target_workspace,
        "target_workspace_summary": target_workspace_summary,
    }


def list_workspace_handoffs(workspace_id: str) -> list[dict[str, object]]:
    try:
        get_workspace_record(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise WorkspaceHandoffError(str(exc)) from exc
    return list(handoff_store.list_handoffs_for_workspace(workspace_id))
