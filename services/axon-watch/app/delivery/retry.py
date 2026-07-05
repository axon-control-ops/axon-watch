"""Retry helper for transient delivery adapter failures."""

from __future__ import annotations

from collections.abc import Callable

DeliveryAttempt = tuple[str, str, str]
DeliverFn = Callable[[], DeliveryAttempt]

_RETRYABLE_MARKERS = (
    "HTTP 429",
    "HTTP 502",
    "HTTP 503",
    "HTTP 504",
    "connection refused",
    "timed out",
    "temporary failure",
)


def is_retryable_error(error: str) -> bool:
    lowered = error.strip().lower()
    if not lowered:
        return False
    return any(marker.lower() in lowered for marker in _RETRYABLE_MARKERS)


def deliver_with_retry(
    deliver_fn: DeliverFn,
    *,
    max_attempts: int = 3,
) -> DeliveryAttempt:
    attempts = max(1, max_attempts)
    last_result: DeliveryAttempt = ("failed", "", "retry_exhausted")

    for attempt in range(1, attempts + 1):
        result, error, policy_reason = deliver_fn()
        last_result = (result, error, policy_reason)
        if result == "succeeded":
            if attempt > 1:
                suffix = f"retry_attempts={attempt}"
                policy_reason = f"{policy_reason};{suffix}" if policy_reason else suffix
            return result, error, policy_reason
        if not is_retryable_error(error) or attempt >= attempts:
            return result, error, policy_reason

    return last_result
