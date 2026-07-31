"""Retry soft-failed cross-workspace handoff autostarts on the scheduler tick.

Handoff routing calls ``operator_start`` immediately; capacity / busy owner can
leave the target ticket ``open`` or leased+queued. Semi keeps continuous
specialist leasing off, so drain those tickets on every tick (bounded) without
turning Full leasing back on.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _task_still_needs_start(task: dict[str, Any] | None) -> bool:
    if task is None:
        return False
    status = str(task.get("status") or "").strip().lower()
    if status == "open":
        return True
    if status != "leased":
        return False
    run_id = str(task.get("run_id") or "").strip()
    if not run_id:
        return True
    # Only retry leased tickets whose run is still queued/starting.
    try:
        from app.runs.service import RunNotFoundError, get_run

        run = get_run(run_id)
    except RunNotFoundError:
        return True
    except Exception:  # noqa: BLE001 — fall through to a soft retry
        return True
    phase = str((run or {}).get("phase") or "").strip().lower()
    return phase in {"", "queued", "starting"}


def retry_pending_handoff_autostarts(*, starts_bound: int = 2) -> list[dict[str, Any]]:
    """Best-effort re-start for open follow-through handoff target tasks.

    Never raises. Skips tasks that are already executing or terminal.
    """
    bound = max(0, min(int(starts_bound), 8))
    if bound <= 0:
        return []

    from app.persistence import handoff_store, task_store
    from app.workspace_handoff_routing import try_autostart_handoff_task

    try:
        follow_through = handoff_store.list_open_follow_through_handoffs(limit=40)
    except Exception:  # noqa: BLE001 — tick must stay alive
        logger.exception("handoff autostart retry: list follow-through failed")
        return []

    # Oldest handoffs first so new chatter cannot starve stuck tickets.
    ordered = sorted(
        follow_through,
        key=lambda row: (
            str(row.get("updated_at") or row.get("created_at") or ""),
            str(row.get("handoff_id") or ""),
        ),
    )

    started: list[dict[str, Any]] = []
    for handoff in ordered:
        if len(started) >= bound:
            break
        handoff_id = str(handoff.get("handoff_id") or "").strip()
        task_id = str(handoff.get("target_task_id") or "").strip()
        if not task_id:
            continue
        try:
            task = task_store.get_task(task_id)
        except Exception:  # noqa: BLE001
            logger.exception("handoff autostart retry: get_task failed for %s", task_id)
            continue
        if not _task_still_needs_start(task):
            continue

        result = try_autostart_handoff_task(task_id)
        status = str(result.get("status") or "").strip().lower()
        if status not in {"started", "queued"}:
            logger.info(
                "handoff autostart retry skipped %s (%s): %s",
                handoff_id,
                task_id,
                result.get("detail") or status or "unknown",
            )
            continue
        started.append(
            {
                "handoff_id": handoff_id,
                "task_id": task_id,
                "run_id": str(result.get("run_id") or "").strip(),
                "status": status,
                "workspace_id": str((task or {}).get("workspace_id") or "").strip(),
            }
        )
    if started:
        logger.info(
            "handoff autostart retry advanced %s ticket(s)",
            len(started),
        )
    return started
