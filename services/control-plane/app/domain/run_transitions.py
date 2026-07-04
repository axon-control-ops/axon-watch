"""Allowed run phase transitions for the canonical thin slice.

The table matches the frozen run-state contract, including the accepted
active->paused amendment documented in
docs/contracts/run-state-stop-resume-amendment-request.md.
"""

from __future__ import annotations

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"starting", "paused"},
    "starting": {"planning", "executing", "paused"},
    "planning": {"awaiting_input", "awaiting_approval", "executing", "paused"},
    "executing": {
        "waiting_external",
        "awaiting_approval",
        "review_ready",
        "completed",
        "failed",
        "paused",
    },
    "waiting_external": {"executing", "paused", "cancelled"},
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
