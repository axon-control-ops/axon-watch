"""Control-plane FastAPI lifespan and test patch stubs."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes.health import _BOOT_ID
from app.runs.service import reconcile_orphaned_runs_on_startup
from app.workspace_agents.scheduler import (
    start_continuous_worker_scheduler,
    stop_continuous_worker_scheduler,
)


@asynccontextmanager
async def control_plane_lifespan(_app: FastAPI):
    # Startup before requests (FastAPI lifespan): reconcile, then start worker tick.
    reconcile_orphaned_runs_on_startup(boot_id=_BOOT_ID)
    scheduler_task = await start_continuous_worker_scheduler()
    try:
        yield
    finally:
        await stop_continuous_worker_scheduler(scheduler_task)


def probe_all_connectors() -> list[dict[str, object]]:
    """Compatibility stub for tests/support/stable_connector_probe.py patch sites."""
    return []
