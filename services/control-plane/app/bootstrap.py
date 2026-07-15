"""Control-plane FastAPI lifespan and test patch stubs."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes.health import _BOOT_ID
from app.runs.service import reconcile_orphaned_runs_on_startup


@asynccontextmanager
async def control_plane_lifespan(_app: FastAPI):
    reconcile_orphaned_runs_on_startup(boot_id=_BOOT_ID)
    yield


def probe_all_connectors() -> list[dict[str, object]]:
    """Compatibility stub for tests/support/stable_connector_probe.py patch sites."""
    return []
