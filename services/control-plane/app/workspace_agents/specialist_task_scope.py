"""Resolve open specialist tasks for terminal scope backfill."""

from __future__ import annotations

import logging
from typing import Any

from app.persistence import task_store

logger = logging.getLogger(__name__)


def find_open_specialist_task(
    workspace_id: str,
    owner_role: str,
    *,
    run_id: str | None = None,
) -> dict[str, Any] | None:
    """Newest open/leased task for a specialist role (any goal, not just verify)."""
    workspace = str(workspace_id or "").strip()
    role = str(owner_role or "").strip().lower()
    cleaned_run = str(run_id or "").strip()
    if not workspace or not role or role in {"lead", "watcher", "overview_agent"}:
        return None

    candidates: list[tuple[int, dict[str, Any]]] = []
    for status in ("leased", "open"):
        for row in task_store.list_tasks(workspace_id=workspace, status=status, limit=100):
            if str(row.get("owner_role") or "").strip().lower() != role:
                continue
            task_id = str(row.get("task_id") or "").strip()
            if not task_id:
                continue
            bound_run = str(row.get("run_id") or "").strip()
            if status == "leased" and bound_run and cleaned_run and bound_run != cleaned_run:
                continue
            score = 0
            if status == "leased" and bound_run == cleaned_run:
                score += 4
            elif status == "leased":
                score += 2
            elif status == "open":
                score += 1
            candidates.append((score, row))

    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (item[0], str(item[1].get("updated_at") or "")),
        reverse=True,
    )
    return candidates[0][1]


def try_lease_open_specialist_task(
    *,
    workspace_id: str,
    owner_role: str,
    lease_holder: str,
    run_id: str | None = None,
) -> dict[str, Any] | None:
    """Lease the newest open specialist ticket so terminal jobs inherit scope."""
    task = find_open_specialist_task(workspace_id, owner_role, run_id=run_id)
    if task is None:
        return None
    status = str(task.get("status") or "").strip().lower()
    task_id = str(task.get("task_id") or "").strip()
    if not task_id:
        return None
    if status == "leased":
        return task
    try:
        return task_store.lease_task(
            task_id,
            lease_holder=lease_holder,
            run_id=str(run_id or "").strip() or None,
        )
    except task_store.TaskLedgerError as exc:
        logger.info("specialist task lease skipped for %s: %s", task_id, exc)
        return task_store.get_task(task_id)


__all__ = [
    "find_open_specialist_task",
    "try_lease_open_specialist_task",
]
