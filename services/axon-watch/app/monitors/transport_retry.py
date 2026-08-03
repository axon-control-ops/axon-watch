"""Shared urllib retry helpers for external monitor probes."""

from __future__ import annotations

import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ReadResponse = Callable[[object], str]


def _failure_message(exc: BaseException) -> str:
    if isinstance(exc, URLError) and exc.reason is not None:
        return _failure_message(exc.reason)
    return str(exc).strip()


def is_transient_transport_error(exc: BaseException) -> bool:
    """Return True for DNS blips, timeouts, and other retryable network faults."""
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, URLError) and exc.reason is not None:
        return is_transient_transport_error(exc.reason)
    message = _failure_message(exc).lower()
    return any(
        marker in message
        for marker in (
            "temporary failure in name resolution",
            "name or service not known",
            "getaddrinfo",
            "network is unreachable",
            "no route to host",
            "connection reset",
            "connection refused",
            "timed out",
            "resource temporarily unavailable",
        )
    )


def urlopen_with_retries(
    request: Request,
    *,
    timeout: float,
    retries: int = 1,
    backoff_seconds: float = 0.5,
    read_response: ReadResponse | None = None,
) -> tuple[int, str]:
    """Perform a GET-like urlopen with bounded retries for transient transport errors."""
    attempts = max(1, int(retries) + 1)
    timeout_value = max(1.0, float(timeout))
    read_body = read_response or (lambda response: response.read().decode("utf-8", errors="replace"))

    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout_value) as response:
                return int(response.status), read_body(response)
        except HTTPError as exc:
            return int(exc.code), exc.read().decode("utf-8", errors="replace")
        except (TimeoutError, URLError, OSError) as exc:
            last_exc = exc
            if attempt + 1 >= attempts or not is_transient_transport_error(exc):
                raise
            delay = max(0.0, float(backoff_seconds)) * (2**attempt)
            if delay:
                time.sleep(delay)

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("urlopen_with_retries exhausted without response")
