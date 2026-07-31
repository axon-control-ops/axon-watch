"""Start open Lead-owned board tickets even when continuous leasing is paused.

Semi / Manual keep specialist continuous leasing off. Lead board tickets still
need the same operator_start + kick path so they do not sit Waiting until Full.

The continuous scheduler loop always ticks (reap/reconcile); new specialist
leases stay Full-only. This pickup runs on every tick before the
``scheduler_enabled`` gate.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _task_sort_key(task: dict[str, Any]) -> tuple[str, str]:
    # Oldest open Lead tickets first so alphabetical workspace ids cannot starve others.
    updated = str(task.get("updated_at") or task.get("created_at") or "")
    task_id = str(task.get("task_id") or "")
    return (updated, task_id)


def pickup_open_lead_board_tasks(*, starts_bound: int = 2) -> list[dict[str, Any]]:
    """Lease/start open ``owner_role=lead`` tasks across companies (bounded).

    Soft-fails per task (capacity, busy Lead, missing staffing). Never raises.
    """
    bound = max(0, min(int(starts_bound), 8))
    if bound <= 0:
        return []

    from app.persistence import task_store
    from app.workspace_agents.config_loader import load_workspace_agent_configs
    from app.workspace_agents.operator_start_task import (
        OperatorStartTaskError,
        operator_start_task,
    )

    try:
        _configs, _defaults, companies, _staffing = load_workspace_agent_configs()
    except Exception:  # noqa: BLE001 — pickup is best-effort
        logger.exception("lead board pickup: failed to load companies")
        return []

    candidates: list[dict[str, Any]] = []
    for workspace_id in companies.keys():
        try:
            open_leads = task_store.list_tasks(
                workspace_id=workspace_id,
                status="open",
                owner_role="lead",
                limit=20,
            )
        except Exception:  # noqa: BLE001 — skip broken workspace ledger
            logger.exception(
                "lead board pickup: list_tasks failed for %s", workspace_id
            )
            continue
        for task in open_leads:
            if not str(task.get("task_id") or "").strip():
                continue
            candidates.append(task)

    candidates.sort(key=_task_sort_key)

    started: list[dict[str, Any]] = []
    for task in candidates:
        if len(started) >= bound:
            break
        task_id = str(task.get("task_id") or "").strip()
        workspace_id = str(task.get("workspace_id") or "").strip()
        try:
            result = operator_start_task(task_id)
        except OperatorStartTaskError as exc:
            logger.info("lead board pickup skipped %s: %s", task_id, exc)
            continue
        except Exception:  # noqa: BLE001 — never block the tick
            logger.exception("lead board pickup failed for %s", task_id)
            continue
        run = result.get("run") or {}
        started.append(
            {
                "workspace_id": workspace_id,
                "task_id": task_id,
                "run_id": str(run.get("run_id") or "").strip(),
                "phase": str(run.get("phase") or "").strip().lower(),
            }
        )
    if started:
        logger.info(
            "lead board pickup started %s Lead ticket(s)",
            len(started),
        )
    return started
