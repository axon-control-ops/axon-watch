"""Operator dismissal for stale employee run cards."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import run_store
from app.runs.service import (
    RunLifecycleError,
    _actor_or_operator,
    append_run_execution_receipt,
)


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _sort_key(run: dict[str, Any]) -> tuple[str, str]:
    stamp = str(run.get("ended_at") or run.get("updated_at") or run.get("started_at") or "")
    return stamp, str(run.get("run_id") or "")


def dismiss_employee_role_runs(
    *,
    workspace_id: str,
    role: str,
    reason: str = "operator cleared agent card",
    max_runs: int = 25,
) -> list[str]:
    """Hide stale terminal employee outcomes from the roster without deleting evidence."""
    cleaned_workspace = str(workspace_id or "").strip()
    cleaned_role = str(role or "").strip().lower()
    if not cleaned_workspace:
        raise RunLifecycleError("workspace_id is required")
    if not cleaned_role:
        raise RunLifecycleError("employee role is required")
    cleaned_reason = " ".join(str(reason or "").split()).strip()
    if not cleaned_reason:
        cleaned_reason = "operator cleared agent card"
    if len(cleaned_reason) > 180:
        cleaned_reason = cleaned_reason[:179].rstrip() + "..."

    candidates = [
        run
        for run in run_store.list_runs()
        if str(run.get("workspace_id") or "").strip() == cleaned_workspace
        and str(run.get("employee_role") or "").strip().lower() == cleaned_role
        and is_terminal_phase(str(run.get("phase") or "").strip())
        and not str(run.get("dismiss_reason") or "").strip()
    ]
    candidates.sort(key=_sort_key, reverse=True)

    dismissed: list[str] = []
    for record in candidates[: max(1, min(int(max_runs), 100))]:
        run_id = str(record.get("run_id") or "").strip()
        if not run_id:
            continue
        append_run_execution_receipt(
            run_id,
            receipt_type="operator_clear_agent_card",
            receipt_summary=cleaned_reason,
            actor=_actor_or_operator(),
            success=True,
            intent="dismiss_employee_run_outcome",
        )
        refreshed = run_store.get_run(run_id)
        if refreshed is None:
            continue
        refreshed["dismiss_reason"] = cleaned_reason
        refreshed["updated_at"] = _utc_now_iso()
        run_store.save_run(refreshed)
        dismissed.append(run_id)
    return dismissed
