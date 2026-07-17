"""Role-scoped prompts for continuous employee-agent shifts."""

from __future__ import annotations

from app.workspace_agents.catalog import _DEFAULT_OWNS
from app.workspace_agents.config_loader import EmployeeConfig


def build_continuous_worker_prompt(*, workspace_id: str, employee: EmployeeConfig) -> str:
    role = str(employee.role or "").strip().lower() or "workspace_agent"
    owns = str(employee.owns or "").strip() or _DEFAULT_OWNS.get(role, "assigned workspace work")
    name = str(employee.name or role).strip() or role
    schedule = str(employee.schedule or "continuous").strip().lower()
    return (
        f"You are {name}, the {role} employee for workspace {workspace_id}. "
        f"You own: {owns}. "
        f"This is a bounded continuous shift ({schedule}). "
        "Inspect the workspace, pick the highest-value in-scope task, do it with receipts, "
        "and summarize what changed. Stay inside your role boundary."
    )
