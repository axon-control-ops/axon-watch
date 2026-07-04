"""Canonical run-state helpers for the control-plane thin slice."""

from __future__ import annotations

RUNNING_PHASES = {"queued", "starting", "planning", "executing"}
WAITING_PHASES = {"awaiting_input", "waiting_external", "paused"}
TERMINAL_PHASES = {"completed", "failed", "cancelled"}

PHASE_TO_STATUS = {
    "queued": "running",
    "starting": "running",
    "planning": "running",
    "executing": "running",
    "awaiting_input": "waiting",
    "waiting_external": "waiting",
    "paused": "waiting",
    "awaiting_approval": "blocked",
    "review_ready": "review",
    "completed": "done",
    "failed": "error",
    "cancelled": "stopped",
}

STOP_PHASES = {
    "queued",
    "starting",
    "planning",
    "executing",
    "waiting_external",
    "awaiting_input",
    "awaiting_approval",
    "paused",
}

RESUME_PHASES = {"paused", "awaiting_input", "review_ready"}


def status_for_phase(phase: str) -> str:
    return PHASE_TO_STATUS[phase]


def is_terminal_phase(phase: str) -> bool:
    return phase in TERMINAL_PHASES


def capability_flags(phase: str) -> dict[str, bool]:
    return {
        "can_stop": phase in STOP_PHASES,
        "can_resume": phase in RESUME_PHASES,
        "can_approve": phase == "awaiting_approval",
        "can_review": phase == "review_ready",
    }
