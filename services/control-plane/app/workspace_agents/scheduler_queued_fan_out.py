"""Promote Lead fan-out queued runs into execution for continuous workers."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import task_store, worker_scheduler_settings_store
from app.runs.begin_execution import begin_execution
from app.runs.service import RunLifecycleError, list_runs
from app.workspace_agents.config_loader import EmployeeConfig
from app.workspace_agents.worker_dispatch import worker_dispatch_enabled

logger = logging.getLogger(__name__)


def dispatch_queued_lead_fan_out_runs(
    *,
    companies: dict[str, Any],
    starts_bound: int,
    active_bound: int,
    executing_run_count: Callable[[], int],
    employee_for_role: Callable[[dict[str, Any], str, str], EmployeeConfig | None],
    dispatch_worker_run: Callable[..., None],
    target_run_id: str | None = None,
) -> list[dict[str, Any]]:
    """Promote queued handoff runs into Lane B without creating duplicate runs."""
    if not worker_dispatch_enabled() or starts_bound <= 0:
        return []
    target = str(target_run_id or "").strip()
    started: list[dict[str, Any]] = []
    queued = [
        run
        for run in list_runs()
        if str(run.get("phase") or "").strip() == "queued"
        and str(run.get("employee_role") or "").strip()
        and str(run.get("task_id") or "").strip()
        and (not target or str(run.get("run_id") or "").strip() == target)
        and not is_terminal_phase(str(run.get("phase") or "").strip())
    ]
    queued.sort(
        key=lambda run: str(run.get("started_at") or run.get("updated_at") or ""),
        reverse=True,  # Newest Lead handoffs first — stale spam must not bury fresh asks.
    )
    for run in queued:
        if len(started) >= starts_bound:
            break
        if executing_run_count() + len(started) >= active_bound:
            break
        workspace_id = str(run.get("workspace_id") or "").strip()
        role = str(run.get("employee_role") or "").strip().lower()
        task_id = str(run.get("task_id") or "").strip()
        run_id = str(run.get("run_id") or "").strip()
        if task_id:
            bound = task_store.get_task(task_id)
            status = str((bound or {}).get("status") or "").strip().lower()
            if status in {"cancelled", "completed", "failed"}:
                if run_id:
                    try:
                        from app.runs.restart_reconcile import interrupt_run_on_restart

                        interrupt_run_on_restart(run_id)
                    except Exception:  # noqa: BLE001
                        pass
                continue
        employee = employee_for_role(companies, workspace_id, role)
        if employee is None:
            continue
        if not worker_scheduler_settings_store.is_employee_enabled(
            workspace_id,
            role,
            file_enabled=bool(employee.enabled),
        ):
            continue
        try:
            advanced = begin_execution(
                str(run["run_id"]),
                actor="workspace_scheduler",
                receipt_summary="Queued fan-out run entered execution for dispatch",
            )
        except RunLifecycleError:
            logger.exception("could not advance queued fan-out run %s", run.get("run_id"))
            continue
        started.append(advanced)
        threading.Thread(
            target=dispatch_worker_run,
            kwargs={
                "workspace_id": workspace_id,
                "employee": employee,
                "run_record": advanced,
            },
            daemon=True,
            name=f"worker-dispatch-queued-{advanced.get('run_id')}",
        ).start()
    return started
