"""Auto-start skip gates for continuous worker ticks (usage + runtime auth)."""

from __future__ import annotations

from app.workspace_agents.failure_detail import is_runtime_auth_failure, is_usage_limit_failure
from app.workspace_agents.run_outcome import latest_role_run_outcome


def usage_limit_blocks_auto_start(workspace_id: str, role: str) -> bool:
    """Skip auto-schedule when the last shift failed on Cursor usage limits."""
    outcome = latest_role_run_outcome(workspace_id, role)
    if not outcome or str(outcome.get("outcome") or "").strip().lower() != "failed":
        return False
    return is_usage_limit_failure(str(outcome.get("detail") or ""))


def workspace_usage_limit_blocks_auto_start(workspace_id: str, roles: list[str]) -> bool:
    """Cursor usage is account-wide — one role's limit failure blocks every continuous start."""
    return any(usage_limit_blocks_auto_start(workspace_id, role) for role in roles)


def runtime_auth_blocks_auto_start(workspace_id: str, role: str) -> bool:
    """Skip auto-schedule when the last shift failed on missing CLI/vault auth."""
    outcome = latest_role_run_outcome(workspace_id, role)
    if not outcome or str(outcome.get("outcome") or "").strip().lower() != "failed":
        return False
    return is_runtime_auth_failure(str(outcome.get("detail") or ""))
