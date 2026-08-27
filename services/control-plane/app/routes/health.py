"""Health and readiness endpoints."""

from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Request

from app.config import _deployment_mode, _public_base_url, _state_dir, _watch_base_url
from app.auth.middleware import resolve_mutating_identity
from app.auth.settings import auth_mode, is_remotely_reachable
from app.persistence import run_store_sqlite

router = APIRouter()
_BOOT_ID = uuid.uuid4().hex


@router.get("/api/health")
@router.get("/health")
def health() -> dict[str, str]:
    return {
        "service": "control-plane",
        "status": "ok",
        "mode": "bootstrap",
        "boot_id": _BOOT_ID,
    }


def _detailed_readiness_allowed(request: Request) -> bool:
    if auth_mode() == "off" and not is_remotely_reachable():
        return True
    identity, _ = resolve_mutating_identity(request)
    return identity is not None


@router.get("/api/readiness")
def readiness(request: Request) -> dict[str, object]:
    detailed = _detailed_readiness_allowed(request)
    base: dict[str, object] = {
        "service": "control-plane",
        "status": "ready",
        "detail": "full" if detailed else "redacted",
    }
    if not detailed:
        return base
    db_path = str(
        run_store_sqlite.resolve_db_path(os.environ.get("AXON_WATCH_CONTROL_PLANE_DB"))
    )
    return {
        **base,
        "mode": _deployment_mode(),
        "watch_base_url": _watch_base_url(),
        "state_dir": _state_dir(),
        "control_plane_db": db_path,
        "public_base_url": _public_base_url(),
    }
