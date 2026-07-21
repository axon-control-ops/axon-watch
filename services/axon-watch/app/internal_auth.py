"""Optional shared-secret gate for watch /internal mutating routes (Gate 2)."""

from __future__ import annotations

import os
import secrets
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_MUTATING = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_HEADER = "x-axon-internal-token"
_EXEMPT_SUFFIXES = (
    "/internal/watch/health",
    "/internal/watch/readiness",
)


def internal_service_token() -> str:
    return os.environ.get("AXON_WATCH_INTERNAL_SERVICE_TOKEN", "").strip()


def _is_exempt(path: str) -> bool:
    cleaned = path.rstrip("/") or "/"
    return any(cleaned == suffix or cleaned.endswith(suffix) for suffix in _EXEMPT_SUFFIXES)


def extract_internal_token(headers: dict[str, str]) -> str:
    for key, value in headers.items():
        if key.lower() == _HEADER:
            return str(value or "").strip()
    return ""


class InternalServiceTokenMiddleware(BaseHTTPMiddleware):
    """When AXON_WATCH_INTERNAL_SERVICE_TOKEN is set, require it on mutating watch routes."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        token = internal_service_token()
        if not token:
            return await call_next(request)
        method = request.method.upper()
        path = request.url.path
        if method not in _MUTATING or _is_exempt(path):
            return await call_next(request)
        presented = extract_internal_token(dict(request.headers))
        if not presented or not secrets.compare_digest(presented, token):
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "watch internal mutating routes require X-Axon-Internal-Token",
                    "auth_required": True,
                },
            )
        return await call_next(request)
