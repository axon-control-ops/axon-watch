"""Approval boundaries for runtime fabric dispatch (Phase G G3.3 / G3.8).

Tool-capable CLI modes may only run when the linked run is in ``executing`` phase.
Consultative tiers (Cursor plan / Codex read-only) stay available without approval.
"""

from __future__ import annotations

import os
from typing import Literal

ExecutionTier = Literal["consultative", "executing"]
ExecutionAccess = Literal["consultative", "full"]

_BLOCKED_PHASES = frozenset(
    {
        "awaiting_approval",
        "awaiting_input",
        "paused",
        "cancelled",
        "completed",
        "failed",
        "queued",
        "starting",
        "planning",
    }
)


def _truthy_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def normalize_execution_access(value: str | None) -> ExecutionAccess:
    normalized = str(value or "consultative").strip().lower()
    return "full" if normalized == "full" else "consultative"


def full_access_requested(execution_access: str | None) -> bool:
    return normalize_execution_access(execution_access) == "full"


def agent_tool_execution_enabled(execution_access: str | None = None) -> bool:
    """When true, Lane B Agent may use tool-capable CLI modes after approval."""
    if full_access_requested(execution_access):
        return True
    return _truthy_env("AXON_WATCH_AGENT_TOOL_EXECUTION", False)


def lane_b_agent_requires_approval(execution_access: str | None = None) -> bool:
    """Whether an agent-mode run must stop at the approval boundary.

    Full Access consent (the explicit dialog in the Agent Dock) *is* the
    approval — those runs go straight to executing. Only the legacy env-flag
    path still requires a per-run approval.
    """
    if full_access_requested(execution_access):
        return False
    return agent_tool_execution_enabled(execution_access)


def resolve_runtime_execution_tier(
    *,
    composer_mode: str,
    run_phase: str | None,
    execution_access: str | None = None,
) -> ExecutionTier:
    normalized_mode = str(composer_mode or "ask").strip().lower()
    if normalized_mode != "agent":
        return "consultative"
    if not agent_tool_execution_enabled(execution_access):
        return "consultative"
    phase = str(run_phase or "").strip().lower()
    if phase == "executing":
        return "executing"
    return "consultative"


def runtime_dispatch_blocked_reason(
    *,
    composer_mode: str,
    run_phase: str | None,
    execution_access: str | None = None,
) -> str | None:
    """Human-readable block reason when tool execution was requested but denied."""
    if not agent_tool_execution_enabled(execution_access):
        return None
    if str(composer_mode or "").strip().lower() != "agent":
        return None
    phase = str(run_phase or "").strip().lower()
    if phase == "executing":
        return None
    if phase == "awaiting_approval":
        return (
            "Run is awaiting operator approval. Approve the run in the Agent Dock or "
            "Mission Control, then send another Agent turn to start Full Access execution."
        )
    if phase and phase in _BLOCKED_PHASES:
        return f"Run phase `{phase}` blocks tool execution until the run is executing."
    if phase:
        return f"Run phase `{phase}` is not eligible for tool execution."
    return None


def consultative_only_notice(
    *,
    composer_mode: str,
    run_phase: str | None,
    execution_access: str | None = None,
) -> str | None:
    """Notice appended when Agent mode falls back to consultative tier."""
    if str(composer_mode or "").strip().lower() != "agent":
        return None
    if (
        resolve_runtime_execution_tier(
            composer_mode=composer_mode,
            run_phase=run_phase,
            execution_access=execution_access,
        )
        == "executing"
    ):
        return None
    blocked = runtime_dispatch_blocked_reason(
        composer_mode=composer_mode,
        run_phase=run_phase,
        execution_access=execution_access,
    )
    if blocked:
        return blocked
    if not agent_tool_execution_enabled(execution_access):
        return (
            "Agent mode is consultative-only. Enable Full Access in the Agent Dock "
            "composer to let the agent edit files and run commands."
        )
    return None
