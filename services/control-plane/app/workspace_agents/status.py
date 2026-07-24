"""Derive workspace and employee agent status from active runs."""

from __future__ import annotations

from typing import Any

from app.domain.run_state import is_terminal_phase
from app.runs.queries import is_background_employee_run
from app.runs.service import list_runs
from app.runs.stale_reconcile import BUSY_EMPLOYEE_PHASES


def status_from_run(run: dict[str, Any]) -> str:
    """Map one run record to a roster status string."""
    phase = str(run.get("phase", "")).strip()
    status = str(run.get("status", "")).strip()

    if phase == "awaiting_approval":
        return "waiting_approval"
    if phase == "planning" or str(run.get("mode", "")).strip() == "plan":
        return "planning"
    if status in {"review", "review_ready"} or phase == "review_ready":
        return "verifying"
    if status == "blocked" or phase in {"paused", "awaiting_input"}:
        return "blocked"
    if phase == "executing":
        return "executing"
    # Queued/starting = assigned ledger work, not mid-shift Lane B yet.
    if phase in {"queued", "starting"}:
        return "assigned"
    if status == "running":
        return "executing"
    return "watching"


def _non_terminal_workspace_runs(
    workspace_id: str,
    *,
    operator_facing: bool = False,
) -> list[dict[str, Any]]:
    normalized = workspace_id.strip()
    runs: list[dict[str, Any]] = []
    for run in list_runs():
        if str(run.get("workspace_id", "")).strip() != normalized:
            continue
        if is_terminal_phase(str(run.get("phase", "")).strip()):
            continue
        if operator_facing and is_background_employee_run(run):
            continue
        runs.append(run)
    return runs


def derive_agent_status(workspace_id: str) -> str:
    """Derive roster status from non-terminal phases only.

    Align with list_active_runs(): ignore ended_at/status ghosts where phase is
    already completed/failed/cancelled but status stayed "running".
    """
    runs = _non_terminal_workspace_runs(workspace_id, operator_facing=True)
    if not runs:
        return "idle"

    runs.sort(key=lambda run: str(run.get("updated_at") or run.get("started_at") or ""), reverse=True)
    return status_from_run(runs[0])


def _busy_role_tagged_runs(workspace_id: str, role: str) -> list[dict[str, Any]]:
    """In-flight role-tagged runs that block another worker start for this role."""
    cleaned_role = str(role or "").strip().lower()
    if not cleaned_role:
        return []
    return [
        run
        for run in _non_terminal_workspace_runs(workspace_id)
        if str(run.get("employee_role") or "").strip().lower() == cleaned_role
        and str(run.get("phase") or "").strip() in BUSY_EMPLOYEE_PHASES
    ]


def active_role_run_status(workspace_id: str, role: str) -> str | None:
    """Return status for the newest in-flight run tagged with this employee role."""
    tagged = _busy_role_tagged_runs(workspace_id, role)
    if not tagged:
        return None
    tagged.sort(key=lambda run: str(run.get("updated_at") or run.get("started_at") or ""), reverse=True)
    return status_from_run(tagged[0])


def active_role_run_id(workspace_id: str, role: str) -> str | None:
    """Return run_id for the newest in-flight run tagged with this employee role."""
    tagged = _busy_role_tagged_runs(workspace_id, role)
    if not tagged:
        return None
    tagged.sort(key=lambda run: str(run.get("updated_at") or run.get("started_at") or ""), reverse=True)
    run_id = str(tagged[0].get("run_id") or "").strip()
    return run_id or None


def employee_status(
    *,
    role: str,
    schedule: str,
    workspace_status: str,
    primary: bool,
    role_run_status: str | None = None,
) -> str:
    # Lead-like roles mirror workspace status; specialists use role_run_status below
    # even when auto-marked primary in a single-employee company roster.
    if role in {"lead", "workspace_agent", "overview_agent"}:
        if workspace_status != "idle":
            return workspace_status
        if schedule == "always_on" or role == "watcher":
            return "watching"
        return "idle"

    # Shared company blockers surface for everyone.
    if workspace_status in {"blocked", "waiting_approval"}:
        return workspace_status

    # Always-on watchers stay on duty; they do not mirror active agent runs.
    if schedule == "always_on" or role == "watcher":
        return "watching"

    # Role specialists reflect their own role-tagged run when present.
    if role_run_status:
        return role_run_status

    # Role specialists stay idle until role-tagged runs exist.
    return "idle"
