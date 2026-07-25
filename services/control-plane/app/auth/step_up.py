"""Step-up confirmation for Full Access and exact-effect (Gate 2 residual)."""

from __future__ import annotations

from starlette.requests import Request

from app.auth.settings import is_remotely_reachable

STEP_UP_HEADER = "x-axon-step-up"
FULL_ACCESS_ACTION = "full-access"
EXACT_EFFECT_ACTION = "exact-effect"


def step_up_header_value(request: Request) -> str:
    return (request.headers.get(STEP_UP_HEADER) or request.headers.get("X-Axon-Step-Up") or "").strip().lower()


def reject_missing_step_up(request: Request, *, action: str) -> str | None:
    """
    When remotely reachable, require an explicit step-up header matching ``action``.

    Local / loopback surfaces skip this so consent UI + body flags remain enough
    for day-to-day operator use. Remote surfaces need both auth and the header
    so a forged body alone cannot escalate to Full Access / exact-effect.
    """
    if not is_remotely_reachable():
        return None
    expected = action.strip().lower()
    if not expected:
        return "step-up action is required"
    presented = step_up_header_value(request)
    if presented != expected:
        return (
            f"step-up confirmation required "
            f"(send header X-Axon-Step-Up: {expected})"
        )
    return None
