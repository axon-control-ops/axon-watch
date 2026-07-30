"""Same-origin guard for mutating API requests (Gate 2 residual)."""

from __future__ import annotations

from urllib.parse import urlparse

from starlette.requests import Request

from app.auth.settings import client_is_loopback, is_remotely_reachable
from app.config import _public_base_url


def _normalize_origin(value: str | None) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def expected_public_origin() -> str | None:
    return _normalize_origin(_public_base_url())


def request_origin(request: Request) -> str | None:
    header = request.headers.get("origin") or request.headers.get("Origin")
    if header:
        return _normalize_origin(header)
    referer = request.headers.get("referer") or request.headers.get("Referer")
    if referer:
        return _normalize_origin(referer)
    return None


def _origin_host_is_loopback(origin: str | None) -> bool:
    if not origin:
        return False
    return client_is_loopback(urlparse(origin).hostname)


def reject_cross_origin_mutation(request: Request) -> str | None:
    """
    When the surface is remotely reachable, reject mutating calls whose Origin
    (or Referer) does not match the configured public base URL.

    Returns an error detail string when the request should be blocked, else None.
    Requests with no Origin/Referer (CLI / server-to-server) are allowed — they
    still require the operator bearer token under local_token mode.

    Loopback operator consoles (Vite :5173 / preview :4173) remain first-class
    even when AXON_WATCH_PUBLIC_BASE_URL points at the public tunnel hostname.
    Browsers set Origin to the page origin, so evil.com cannot forge a loopback
    Origin; bearer auth still applies for remote clients.
    """
    if not is_remotely_reachable():
        return None
    expected = expected_public_origin()
    if not expected:
        return None
    presented = request_origin(request)
    if presented is None:
        return None
    if presented == expected:
        return None
    if _origin_host_is_loopback(presented):
        return None
    return f"cross-origin mutation blocked (origin {presented} != {expected})"
