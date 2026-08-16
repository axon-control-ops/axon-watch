"""Control-plane FastAPI lifespan and test patch stubs."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes.health import _BOOT_ID
from app.runs.service import (
    drain_terminal_employee_runs,
    reap_abandoned_review_ready_runs,
    reap_stale_employee_runs,
    reconcile_orphaned_runs_on_startup,
)
from app.workspace_agents.scheduler import (
    start_continuous_worker_scheduler,
    stop_continuous_worker_scheduler,
)

logger = logging.getLogger(__name__)


def _log_auth_posture() -> None:
    """Make the effective auth posture visible on every boot.

    auth_mode() only forces local_token when AXON_WATCH_PUBLIC_BASE_URL (or
    AXON_WATCH_REMOTELY_REACHABLE) correctly reflects real reachability — a
    process bound to 0.0.0.0 without that env set still resolves to "off"
    silently. This doesn't change the default (would risk breaking local dev
    setups relying on it); it just stops that gap from being invisible.
    """
    from app.auth.settings import auth_mode, is_remotely_reachable

    mode = auth_mode()
    reachable = is_remotely_reachable()
    if mode == "off":
        logger.warning(
            "auth_mode=off (reachable=%s) — mutating API routes accept anonymous "
            "requests. If this process is reachable beyond localhost, set "
            "AXON_WATCH_PUBLIC_BASE_URL to its real address or "
            "AXON_WATCH_REMOTELY_REACHABLE=1 to force local_token.",
            reachable,
        )
    else:
        logger.info("auth_mode=%s (reachable=%s)", mode, reachable)


@asynccontextmanager
async def control_plane_lifespan(_app: FastAPI):
    # Startup before requests (FastAPI lifespan): reconcile, then start worker tick.
    _log_auth_posture()
    try:
        from app.cli_runtime.composer_sandbox import reconcile_persisted_sandboxes

        reconcile_persisted_sandboxes()
    except Exception:  # noqa: BLE001 — recovery failure must remain visible without blocking boot
        logger.exception("composer Sandbox startup reconciliation failed")
    reconcile_orphaned_runs_on_startup(boot_id=_BOOT_ID)
    abandoned = reap_abandoned_review_ready_runs()
    if abandoned:
        logger.info(
            "startup abandoned review_ready reap completed %s run(s)",
            len(abandoned),
        )
    reaped = reap_stale_employee_runs()
    if reaped:
        logger.info(
            "startup stale employee-run reap cleared %s run(s)",
            len(reaped),
        )
    pruned = drain_terminal_employee_runs()
    if pruned:
        logger.info(
            "startup employee run retention drained %s terminal run(s)",
            len(pruned),
        )
    try:
        from app.host_context.reminders import migrate_whatsapp_g42_reminder

        migrate_whatsapp_g42_reminder(due_hours=24)
    except Exception:  # noqa: BLE001 — reminder migration must not block boot
        logger.exception("whatsapp g42 reminder migration failed")
    scheduler_task = await start_continuous_worker_scheduler()
    try:
        yield
    finally:
        await stop_continuous_worker_scheduler(scheduler_task)


def probe_all_connectors() -> list[dict[str, object]]:
    """Compatibility stub for tests/support/stable_connector_probe.py patch sites."""
    return []
