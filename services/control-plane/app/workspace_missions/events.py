"""Best-effort task-to-mission lifecycle bridge."""

from __future__ import annotations

from typing import Any


def notify_task_terminal(task: dict[str, Any]) -> None:
    task_id = str(task.get("task_id") or "").strip()
    status = str(task.get("status") or "").strip()
    if not task_id or status not in {"completed", "failed", "cancelled"}:
        return
    try:
        from app.workspace_missions.service import auto_create_mission_for_task, kick_missions_for_task

        if status == "completed":
            auto_create_mission_for_task(task_id)
        kick_missions_for_task(task_id)
    except Exception:
        return


__all__ = ["notify_task_terminal"]
