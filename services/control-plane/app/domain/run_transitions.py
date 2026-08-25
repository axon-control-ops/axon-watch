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
    # ``failed`` is reachable from every non-terminal phase that fail_run()
    # already accepts as input (executing / review_ready / paused). Without it
    # the guard in fail_run and this table disagreed: fail_run let a paused or
    # review_ready run through, then _transition_record refused the move and
    # raised RunLifecycleError. fail_worker_run swallows that error, so the run
    # never reached a terminal phase and sat "paused" or "review_ready"
    # forever -- the stale runs operators kept having to clear by hand.
    "paused": {"executing", "cancelled", "completed", "failed"},
    "review_ready": {"completed", "executing", "failed"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}


def can_transition(from_phase: str, to_phase: str) -> bool:
    return to_phase in ALLOWED_TRANSITIONS.get(from_phase, set())
