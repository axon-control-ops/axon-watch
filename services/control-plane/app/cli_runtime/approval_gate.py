"""Approval boundaries for runtime fabric dispatch (Phase G G3.3 / G3.8).

Tool-capable CLI modes may only run when the linked run is in ``executing`` phase.
Consultative tiers (Cursor plan / Codex read-only) stay available without approval.
"""

from __future__ import annotations

import os
from typing import Literal

ExecutionTier = Literal["consultative", "executing"]
ExecutionAccess = Literal["consultative", "full"]

# Modes that create linked runs and may use tool-capable CLI execution.
_TOOL_CAPABLE_COMPOSER_MODES = frozenset({"agent", "debug"})
# Modes that create a linked run for stop / resume / recovery (includes Plan).
_RUN_LINKED_COMPOSER_MODES = frozenset({"agent", "debug", "plan"})

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


def is_tool_capable_composer_mode(composer_mode: str | None) -> bool:
    """True for Agent and Debug — modes that may edit files / run tools after consent."""
    return str(composer_mode or "").strip().lower() in _TOOL_CAPABLE_COMPOSER_MODES


def is_run_linked_composer_mode(composer_mode: str | None) -> bool:
    """True for modes that create a linked run (Agent, Debug, and Plan)."""
    return str(composer_mode or "").strip().lower() in _RUN_LINKED_COMPOSER_MODES


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
    if not is_tool_capable_composer_mode(composer_mode):
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
    if not is_tool_capable_composer_mode(composer_mode):
        return None
    mode_label = str(composer_mode or "agent").strip().lower() or "agent"
    phase = str(run_phase or "").strip().lower()
    if phase == "executing":
        return None
    if phase == "awaiting_approval":
        return (
            "Run is awaiting operator approval. Approve the run in the Agent Dock or "
            "Mission Control, then send another "
            f"{mode_label.capitalize()} turn to start Full Access execution."
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
    """Notice appended when Agent/Debug mode falls back to consultative tier."""
    if not is_tool_capable_composer_mode(composer_mode):
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
        mode_label = str(composer_mode or "agent").strip().lower() or "agent"
        return (
            f"{mode_label.capitalize()} mode is consultative-only. Enable Full Access in the "
            "Agent Dock composer to let the agent edit files and run commands."
        )
    return None
