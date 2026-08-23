"""Desktop bootstrap + static SPA routes for packaged VAXON."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.auth.desktop_session import (
    SESSION_COOKIE,
    SESSION_COOKIE_MAX_AGE_SECONDS,
    consume_bootstrap_code,
    extract_session_token,
    issue_session_token,
    mint_bootstrap_code,
    validate_session_token,
)
from app.auth.settings import (
    allow_loopback_bypass,
    auth_mode,
    client_is_loopback,
    operator_token,
)

router = APIRouter()
spa_router = APIRouter()


class DesktopBootstrapRequest(BaseModel):
    bootstrap_code: str | None = Field(default=None, min_length=8)
    operator_token: str | None = None


class OperatorSessionRequest(BaseModel):
    operator_token: str = Field(min_length=1)


def console_dist_dir() -> Path | None:
    raw = (os.environ.get("AXON_WATCH_CONSOLE_DIST") or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    if path.is_dir() and (path / "index.html").is_file():
        return path
    return None


def _token_matches(presented: str) -> bool:
    expected = (operator_token() or "").strip()
    return bool(expected and presented and secrets.compare_digest(presented, expected))


def _request_bearer(request: Request) -> str:
    header = request.headers.get("authorization") or ""
    parts = header.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return (request.headers.get("x-axon-operator-token") or "").strip()


def _session_meta() -> dict[str, object]:
    return {
        "auth_mode": auth_mode(),
        "loopback_bypass": allow_loopback_bypass(),
        "cookie_max_age_seconds": SESSION_COOKIE_MAX_AGE_SECONDS,
    }


def _session_status(request: Request) -> dict[str, object]:
    meta = _session_meta()
    mode = str(meta["auth_mode"])
    if mode == "off":
        return {"authenticated": True, "auth_required": False, "identity": "local", **meta}
    if _token_matches(_request_bearer(request)):
        return {"authenticated": True, "auth_required": True, "identity": "operator", **meta}
    if validate_session_token(extract_session_token(request.cookies, request.headers)):
        return {"authenticated": True, "auth_required": True, "identity": "session", **meta}
    client_host = request.client.host if request.client else None
    if meta["loopback_bypass"] and client_is_loopback(client_host):
        return {"authenticated": True, "auth_required": False, "identity": "loopback", **meta}
    return {"authenticated": False, "auth_required": True, "identity": None, **meta}


def _request_is_secure(request: Request) -> bool:
    forwarded = (request.headers.get("x-forwarded-proto") or "").split(",", 1)[0].strip()
    return forwarded == "https" or request.url.scheme == "https"


def _set_session_cookie(response: Response, *, secure: bool, same_site: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=issue_session_token(),
        httponly=True,
        samesite=same_site,
        secure=secure,
        max_age=SESSION_COOKIE_MAX_AGE_SECONDS,
        path="/",
    )


@router.get("/api/auth/session")
def operator_session_status(request: Request) -> dict[str, object]:
    """Report whether this browser may use protected operator actions."""
    return _session_status(request)


@router.post("/api/auth/session")
def operator_session_login(
    body: OperatorSessionRequest,
    request: Request,
    response: Response,
) -> dict[str, object]:
    """Exchange the deployment operator token for an HttpOnly browser session."""
    if not operator_token():
        raise HTTPException(status_code=503, detail="operator token is not configured")
    if not _token_matches(body.operator_token.strip()):
        raise HTTPException(status_code=401, detail="invalid operator token")
    _set_session_cookie(
        response,
        secure=_request_is_secure(request),
        same_site="strict",
    )
    status = _session_status(request)
    status.update({"authenticated": True, "auth_required": True, "identity": "session"})
    return status


@router.delete("/api/auth/session")
def operator_session_logout(response: Response) -> dict[str, object]:
    """Clear the browser session without changing the deployment token."""
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        httponly=True,
        samesite="strict",
    )
    return {"authenticated": False, "auth_required": True, "identity": None, **_session_meta()}


@router.post("/api/desktop/bootstrap-code")
def desktop_bootstrap_code(request: Request) -> dict[str, object]:
    """Mint a short-lived bootstrap code (desktop shell only; requires bearer)."""
    header = request.headers.get("authorization") or ""
    parts = header.split(None, 1)
    presented = parts[1].strip() if len(parts) == 2 and parts[0].lower() == "bearer" else ""
    if not _token_matches(presented):
        raise HTTPException(status_code=401, detail="operator token required")
    return {"bootstrap_code": mint_bootstrap_code(), "ttl_seconds": 120}


@router.post("/api/desktop/bootstrap")
def desktop_bootstrap(body: DesktopBootstrapRequest, response: Response) -> dict[str, object]:
    """Exchange operator token (+ optional one-time code) for an HttpOnly session cookie."""
    presented = (body.operator_token or "").strip()
    token_ok = _token_matches(presented)
    code = (body.bootstrap_code or "").strip()
    code_ok = consume_bootstrap_code(code) if code else True
    if not (token_ok and code_ok):
        raise HTTPException(status_code=401, detail="invalid desktop bootstrap credentials")

    _set_session_cookie(response, secure=False, same_site="lax")
    return {"ok": True, "session": True}


@router.get("/api/desktop/status")
def desktop_status() -> dict[str, object]:
    return {
        "console_dist": str(console_dist_dir()) if console_dist_dir() else None,
        "packaged": console_dist_dir() is not None,
        "deployment_mode": os.environ.get("AXON_WATCH_DEPLOYMENT_MODE", "bootstrap"),
    }


@spa_router.get("/")
@spa_router.get("/index.html")
def spa_index() -> Response:
    dist = console_dist_dir()
    if dist is None:
        raise HTTPException(status_code=404, detail="console dist not configured")
    return FileResponse(dist / "index.html")


@spa_router.get("/{asset_path:path}")
def spa_assets(asset_path: str) -> Response:
    """Serve SPA assets; fall back to index.html for client-side routes."""
    if asset_path.startswith("api/") or asset_path == "api":
        raise HTTPException(status_code=404, detail="not found")
    dist = console_dist_dir()
    if dist is None:
        raise HTTPException(status_code=404, detail="console dist not configured")
    candidate = (dist / asset_path).resolve()
    try:
        candidate.relative_to(dist)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="not found") from exc
    if candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(dist / "index.html")


def register_desktop_routes(app: FastAPI) -> None:
    app.include_router(router)
    if console_dist_dir() is not None:
        app.include_router(spa_router)
