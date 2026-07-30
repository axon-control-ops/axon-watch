"""In-process mutating-API rate limit (Gate 2 residual)."""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque

from starlette.requests import Request

_LOCK = threading.Lock()
_HITS: dict[str, deque[float]] = defaultdict(deque)


def mutating_rate_limit_per_minute() -> int:
    raw = os.environ.get("AXON_WATCH_MUTATING_RATE_LIMIT_PER_MINUTE", "120").strip()
    try:
        value = int(raw)
    except ValueError:
        return 120
    return max(0, value)


def _mutation_scope(request: Request) -> str:
    """Keep one noisy API family from starving unrelated operator controls."""
    parts = [part for part in request.url.path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "api":
        return f"/api/{parts[1]}"
    return f"/{parts[0]}" if parts else "/"


def _client_key(request: Request, identity: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{identity}:{host}:{_mutation_scope(request)}"


def reject_mutating_rate_limit(request: Request, *, identity: str) -> str | None:
    """
    Return an error detail when the identity+client+API-family exceeds the window.

    Workers and the browser commonly share the loopback operator identity. Scoping
    by API family prevents task lease/complete bursts from blocking Team chat,
    speech, or run controls while retaining a bounded limit for each surface.
    Limit ``0`` disables enforcement. Window is 60 seconds.
    """
    limit = mutating_rate_limit_per_minute()
    if limit <= 0:
        return None
    key = _client_key(request, identity)
    now = time.monotonic()
    window_start = now - 60.0
    with _LOCK:
        bucket = _HITS[key]
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= limit:
            return (
                f"mutating API rate limit exceeded ({limit}/minute); "
                "slow down and retry"
            )
        bucket.append(now)
    return None


def reset_rate_limit_state_for_tests() -> None:
    with _LOCK:
        _HITS.clear()
