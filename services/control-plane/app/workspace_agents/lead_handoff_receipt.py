"""Record a completed Lead role-run for successful handoff fast paths.

Lead decompose / fan-out intentionally skip a Lane B Lead essay. Without a
terminal Lead run, roster `last_outcome` stays stuck on an older failure and
the IDE Soft Attention strip keeps showing LAST JOB FAILED even though
specialists were queued successfully.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def record_lead_handoff_run(
    *,
    workspace_id: str,
    summary: str,
    detail: str,
) -> dict[str, Any] | None:
    """Create and complete a Lead handoff run (no task / no Gate 6 acceptance)."""
    cleaned_workspace = str(workspace_id or "").strip()
    if not cleaned_workspace:
        return None
    goal = " ".join(str(summary or "").split()).strip() or "Lead handoff"
    if len(goal) > 180:
        goal = f"{goal[:179].rstrip()}…"
    receipt = " ".join(str(detail or "").split()).strip() or (
        "Lead handoff materialized; specialists queued"
    )
    try:
        from app.runs.service import RunLifecycleError, complete_run, create_run

        created = create_run(
            workspace_id=cleaned_workspace,
            mode="agent",
            summary=goal,
            detail=receipt,
            employee_role="lead",
            enter_execution=True,
        )
        run_id = str(created.get("run_id") or "").strip()
        if not run_id:
            return None
        return complete_run(run_id)
    except RunLifecycleError:
        logger.exception("lead handoff receipt lifecycle failed for %s", cleaned_workspace)
        return None
    except Exception:  # noqa: BLE001 — handoff chat must still succeed
        logger.exception("lead handoff receipt failed for %s", cleaned_workspace)
        return None


__all__ = ["record_lead_handoff_run"]
