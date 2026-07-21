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
    consume_bootstrap_code,
    issue_session_token,
    mint_bootstrap_code,
)
from app.auth.settings import operator_token

router = APIRouter()
spa_router = APIRouter()


class DesktopBootstrapRequest(BaseModel):
    bootstrap_code: str | None = Field(default=None, min_length=8)
    operator_token: str | None = None


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

    session = issue_session_token()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session,
        httponly=True,
        samesite="lax",
        secure=False,  # loopback http://127.0.0.1
        max_age=60 * 60 * 24 * 30,
        path="/",
    )
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
