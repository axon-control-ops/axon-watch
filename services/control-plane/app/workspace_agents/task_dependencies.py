"""Shared task dependency checks for lease, dispatch, and operator start."""

from __future__ import annotations

from typing import Any

from app.persistence import task_store


def dependencies_completed(task: dict[str, Any] | None) -> bool:
    if not isinstance(task, dict):
        return True
    return not dependency_blockers(task)


def dependency_blockers(task: dict[str, Any] | None) -> list[dict[str, str]]:
    if not isinstance(task, dict):
        return []
    deps = task.get("dependencies")
    if not isinstance(deps, list) or not deps:
        return []
    blockers: list[dict[str, str]] = []
    for dep_id in deps:
        cleaned = str(dep_id or "").strip()
        if not cleaned:
            continue
        dep = task_store.get_task(cleaned)
        if dep is None:
            blockers.append(
                {
                    "task_id": cleaned,
                    "status": "missing",
                    "owner_role": "",
                    "summary": "missing dependency",
                }
            )
            continue
        status = str(dep.get("status") or "").strip().lower()
        if status != "completed":
            goal = str(dep.get("goal") or "").strip()
            blockers.append(
                {
                    "task_id": cleaned,
                    "status": status or "unknown",
                    "owner_role": str(dep.get("owner_role") or "").strip().lower(),
                    "summary": goal[:120] if goal else cleaned,
                }
            )
    return blockers


def dependency_blocker_message(task: dict[str, Any] | None) -> str:
    blockers = dependency_blockers(task)
    if not blockers:
        return ""
    parts: list[str] = []
    for row in blockers[:3]:
        role = row.get("owner_role") or "task"
        status = row.get("status") or "unknown"
        task_id = row.get("task_id") or ""
        parts.append(f"{role} {task_id} ({status})")
    suffix = f" (+{len(blockers) - 3} more)" if len(blockers) > 3 else ""
    return f"blocked by unfinished dependencies: {', '.join(parts)}{suffix}"


__all__ = [
    "dependencies_completed",
    "dependency_blocker_message",
    "dependency_blockers",
]
