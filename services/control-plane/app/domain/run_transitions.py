"""Allowed run phase transitions from the frozen run-state contract."""

from __future__ import annotations

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"starting"},
    "starting": {"planning", "executing"},
    "planning": {"awaiting_input", "awaiting_approval", "executing"},
    "executing": {
        "waiting_external",
        "awaiting_approval",
        "review_ready",
        "completed",
        "failed",
    },
    "waiting_external": {"executing", "paused"},
    "awaiting_input": {"planning", "cancelled"},
    "awaiting_approval": {"executing", "cancelled"},
    "paused": {"executing", "cancelled"},
    "review_ready": {"completed", "executing"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}


def can_transition(from_phase: str, to_phase: str) -> bool:
    return to_phase in ALLOWED_TRANSITIONS.get(from_phase, set())
