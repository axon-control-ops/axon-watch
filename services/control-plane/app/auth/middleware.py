"""Mutating-route auth middleware for Gate 2."""

from __future__ import annotations

import secrets
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.auth.desktop_session import extract_session_token, validate_session_token
from app.auth.identity import bind_request_identity, reset_identity_token
from app.auth.origin_guard import reject_cross_origin_mutation
from app.auth.rate_limit import reject_mutating_rate_limit
from app.auth.settings import (
    allow_loopback_bypass,
    auth_mode,
    client_is_loopback,
    operator_token,
)

_MUTATING = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_SENSITIVE_GET_PREFIXES = (
    "/api/agents",
    "/api/briefing",
    "/api/chat",
    "/api/company-roles",
    "/api/connectors",
    "/api/data",
    "/api/delivery",
    "/api/dev/debug-session-log",
    "/api/email",
    "/api/host",
    "/api/inbox",
    "/api/kairo",
    "/api/lead",
    "/api/live",
    "/api/monitors",
    "/api/operator",
    "/api/operator-presence",
    "/api/platform/autonomy",
    "/api/platform/doctor",
    "/api/plans",
    "/api/recovery",
    "/api/runs",
    "/api/runtime",
    "/api/safe-improvement",
    "/api/skills",
    "/api/tasks",
    "/api/tunnel",
    "/api/vault",
    "/api/vault/secrets",
    "/api/vault/export",
    "/api/vault/provider-keys",
    "/api/watch",
    "/api/worker-scheduler",
    "/api/workspace-missions",
    "/api/workspaces",
)
_EXEMPT_PREFIXES = (
    "/api/health",
    # Browser login/logout must remain reachable before a session exists.
    "/api/auth/session",
    "/api/desktop/bootstrap",
    "/api/desktop/bootstrap-code",
    "/api/desktop/status",
    # Gate 9: GitHub signs with X-Hub-Signature-256 (no operator bearer).
    "/api/webhooks/github",
    "/docs",
    "/openapi.json",
    "/redoc",
)


def _is_exempt(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in _EXEMPT_PREFIXES)


def _is_sensitive_get(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in _SENSITIVE_GET_PREFIXES)


def _extract_bearer(request: Request) -> str:
    header = request.headers.get("authorization") or request.headers.get("Authorization") or ""
    parts = header.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    # Same-origin console can also send a dedicated header once wired.
    return (request.headers.get("x-axon-operator-token") or "").strip()


def resolve_mutating_identity(request: Request) -> tuple[str | None, str | None]:
    """Return (identity, error_detail). identity None means reject."""
    mode = auth_mode()
    if mode == "off":
        return "anonymous", None

    token = operator_token()
    presented = _extract_bearer(request)
    if token and presented and secrets.compare_digest(presented, token):
        return "operator", None

    session = extract_session_token(request.cookies, request.headers)
    if validate_session_token(session):
        return "desktop_session", None

    client_host = request.client.host if request.client else None
    if allow_loopback_bypass() and client_is_loopback(client_host):
        return "loopback", None

    if mode == "local_token":
        if not token:
            return None, "AXON_WATCH_OPERATOR_TOKEN is not configured"
        return None, "mutating API requires Authorization: Bearer <operator token>"

    return "anonymous", None


class MutatingAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method.upper()
        path = request.url.path
        identity = "anonymous"
        token = None
        try:
            requires_identity = (method in _MUTATING and not _is_exempt(path)) or (
                method == "GET" and _is_sensitive_get(path)
            )
            if requires_identity:
                if method in _MUTATING:
                    origin_error = reject_cross_origin_mutation(request)
                    if origin_error is not None:
                        return JSONResponse(
                            status_code=403,
                            content={
                                "detail": origin_error,
                                "auth_required": True,
                                "csrf_blocked": True,
                            },
                        )
                resolved, error = resolve_mutating_identity(request)
                if resolved is None:
                    return JSONResponse(
                        status_code=401,
                        content={
                            "detail": error or "unauthorized",
                            "auth_required": True,
                        },
                    )
                identity = resolved
                if method in _MUTATING:
                    rate_error = reject_mutating_rate_limit(request, identity=identity)
                    if rate_error is not None:
                        return JSONResponse(
                            status_code=429,
                            content={
                                "detail": rate_error,
                                "rate_limited": True,
                            },
                        )
            token = bind_request_identity(identity)
            return await call_next(request)
        finally:
            if token is not None:
                reset_identity_token(token)
            else:
                bind_request_identity("anonymous")
