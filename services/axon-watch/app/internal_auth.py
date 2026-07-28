"""Watch service identity: shared token + optional mTLS peer checks (Gate 2 close)."""

from __future__ import annotations

import os
import secrets
from collections.abc import Callable
from urllib.parse import urlparse

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


def _host_is_loopback(host: str | None) -> bool:
    cleaned = str(host or "").strip().lower().split("%", 1)[0]
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    return cleaned in {"127.0.0.1", "localhost", "::1", "0:0:0:0:0:0:0:1"}


def is_remotely_reachable() -> bool:
    forced = os.environ.get("AXON_WATCH_REMOTELY_REACHABLE", "").strip().lower()
    if forced in {"1", "true", "yes", "on"}:
        return True
    if forced in {"0", "false", "no", "off"}:
        return False
    public = os.environ.get("AXON_WATCH_PUBLIC_BASE_URL", "").strip()
    if not public:
        return False
    host = urlparse(public).hostname
    return not _host_is_loopback(host)


def vault_auto_unlock_allowed() -> bool:
    """
    Whether vault auto-unlock may run on this host.

    Default: refused when remotely reachable (Gate 2). Trusted always-on
    operator hosts may opt in with AXON_WATCH_ALLOW_VAULT_AUTO_UNLOCK=1 without
    disabling the rest of remote auth containment.
    """
    raw = os.environ.get("AXON_WATCH_ALLOW_VAULT_AUTO_UNLOCK", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return not is_remotely_reachable()


def mtls_required() -> bool:
    """
    Require a verified client certificate (or proxy-verified equivalent).

    Enable explicitly with AXON_WATCH_MTLS_REQUIRED=1, or automatically when a CA
    file is configured (AXON_WATCH_MTLS_CA_FILE).
    """
    forced = os.environ.get("AXON_WATCH_MTLS_REQUIRED", "").strip().lower()
    if forced in {"1", "true", "yes", "on"}:
        return True
    if forced in {"0", "false", "no", "off"}:
        return False
    return bool(os.environ.get("AXON_WATCH_MTLS_CA_FILE", "").strip())


def client_certificate_verified(request: Request) -> bool:
    """
    Accept reverse-proxy verified client certs (nginx/caddy style headers).

    Direct uvicorn mTLS is optional; most Axon-X deploys terminate TLS at the
    proxy and forward verification headers to the watch service.
    """
    verify = (
        request.headers.get("x-ssl-client-verify")
        or request.headers.get("ssl-client-verify")
        or request.headers.get("x-client-cert-verified")
        or ""
    ).strip().upper()
    if verify in {"SUCCESS", "SUCCESSFUL", "OK", "TRUE", "1", "YES"}:
        allowed_cn = os.environ.get("AXON_WATCH_MTLS_ALLOWED_CN", "").strip()
        if not allowed_cn:
            return True
        presented = (
            request.headers.get("x-ssl-client-s-dn")
            or request.headers.get("ssl-client-s-dn")
            or request.headers.get("x-client-cert-cn")
            or ""
        )
        return allowed_cn.lower() in presented.lower()
    return False


def _is_exempt(path: str) -> bool:
    cleaned = path.rstrip("/") or "/"
    return any(cleaned == suffix or cleaned.endswith(suffix) for suffix in _EXEMPT_SUFFIXES)


def extract_internal_token(headers: dict[str, str]) -> str:
    for key, value in headers.items():
        if key.lower() == _HEADER:
            return str(value or "").strip()
    return ""


class InternalServiceTokenMiddleware(BaseHTTPMiddleware):
    """
    Gate mutating /internal/watch/* routes.

    - Remotely reachable deployments require AXON_WATCH_INTERNAL_SERVICE_TOKEN.
    - When configured, the shared token must match.
    - When mTLS is required, a proxy-verified client certificate is also required.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method.upper()
        path = request.url.path
        if method not in _MUTATING or _is_exempt(path):
            return await call_next(request)

        token = internal_service_token()
        if is_remotely_reachable() and not token:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": (
                        "AXON_WATCH_INTERNAL_SERVICE_TOKEN is required when the "
                        "operator surface is remotely reachable"
                    ),
                    "auth_required": True,
                    "service_identity_required": True,
                },
            )

        if token:
            presented = extract_internal_token(dict(request.headers))
            if not presented or not secrets.compare_digest(presented, token):
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "watch internal mutating routes require X-Axon-Internal-Token",
                        "auth_required": True,
                    },
                )

        if mtls_required() and not client_certificate_verified(request):
            return JSONResponse(
                status_code=401,
                content={
                    "detail": (
                        "watch internal mutating routes require verified mTLS "
                        "(proxy X-SSL-Client-Verify: SUCCESS)"
                    ),
                    "auth_required": True,
                    "mtls_required": True,
                },
            )

        return await call_next(request)
