"""Operator-readable probe failure strings for watch health checks."""

from __future__ import annotations

from urllib.error import URLError


def _probe_failure_message(exc: BaseException) -> str:
    """Extract the most specific operator-readable fragment from a probe exception."""
    if isinstance(exc, URLError) and exc.reason is not None:
        return _probe_failure_message(exc.reason)
    return str(exc).strip()


def _is_timeout_error(exc: BaseException) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, URLError) and exc.reason is not None:
        return _is_timeout_error(exc.reason)
    return False


def format_probe_failure(exc: BaseException, health_url: str) -> str:
    """Turn urllib/OS probe errors into operator-readable health-check detail."""
    message = _probe_failure_message(exc)
    lowered = message.lower()
    if "connection refused" in lowered:
        return f"Connection refused on {health_url}"
    if _is_timeout_error(exc) or "timed out" in lowered:
        return f"Timed out on {health_url}"
    if (
        "name or service not known" in lowered
        or "getaddrinfo" in lowered
        or "temporary failure in name resolution" in lowered
    ):
        return f"Host unreachable on {health_url}"
    if "network is unreachable" in lowered or "no route to host" in lowered:
        return f"Network unreachable on {health_url}"
    if "connection reset" in lowered:
        return f"Connection reset on {health_url}"
    if "ssl" in lowered or "certificate" in lowered:
        return f"TLS error on {health_url}"
    return "probe failed"
