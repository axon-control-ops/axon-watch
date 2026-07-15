"""Derive workspace and employee agent status from active runs."""

from __future__ import annotations

from app.domain.run_state import is_terminal_phase
from app.runs.service import list_runs


def derive_agent_status(workspace_id: str) -> str:
    """Derive roster status from non-terminal phases only.

    Align with list_active_runs(): ignore ended_at/status ghosts where phase is
    already completed/failed/cancelled but status stayed "running".
    """
    runs = [
        run
        for run in list_runs()
        if str(run.get("workspace_id", "")).strip() == workspace_id.strip()
        and not is_terminal_phase(str(run.get("phase", "")).strip())
    ]
    if not runs:
        return "idle"

    runs.sort(key=lambda run: str(run.get("updated_at") or run.get("started_at") or ""), reverse=True)
    primary = runs[0]
    phase = str(primary.get("phase", "")).strip()
    status = str(primary.get("status", "")).strip()

    if phase == "awaiting_approval":
        derived = "waiting_approval"
    elif phase == "planning" or str(primary.get("mode", "")).strip() == "plan":
        derived = "planning"
    elif status in {"review", "review_ready"} or phase == "review_ready":
        derived = "verifying"
    elif status == "blocked" or phase in {"paused", "awaiting_input"}:
        derived = "blocked"
    elif phase == "executing":
        derived = "executing"
    elif phase in {"queued", "starting"} or status == "running":
        derived = "executing"
    else:
        derived = "watching"
    return derived



def employee_status(*, role: str, schedule: str, workspace_status: str, primary: bool) -> str:
    if primary or role in {"lead", "workspace_agent", "overview_agent"}:
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

    # Role specialists stay idle until role-tagged runs exist.
    return "idle"