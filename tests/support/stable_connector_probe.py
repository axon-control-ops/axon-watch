"""Deterministic connector probe results for watch inbox unit/integration tests."""

from __future__ import annotations

from unittest.mock import patch

STABLE_OK_CONNECTOR_RECORDS: list[dict[str, object]] = [
    {
        "connector_id": "control_plane",
        "display_name": "Control plane",
        "health_url": "http://127.0.0.1:8787/api/health",
        "required": True,
        "workspace_id": "workspace_axon_watch",
        "status": "ok",
        "detail": "reachable",
        "last_checked_at": "2026-07-05T08:00:00Z",
        "latency_ms": 1,
    },
    {
        "connector_id": "console_web",
        "display_name": "Console web",
        "health_url": "http://127.0.0.1:4173/",
        "required": True,
        "workspace_id": "workspace_axon_watch",
        "status": "ok",
        "detail": "reachable",
        "last_checked_at": "2026-07-05T08:00:00Z",
        "latency_ms": 1,
    },
    {
        "connector_id": "axon_local",
        "display_name": "axon-local (legacy)",
        "health_url": "http://127.0.0.1:7734/api/health",
        "required": False,
        "workspace_id": "workspace_axon_local",
        "status": "unavailable",
        "detail": "optional probe skipped in tests",
        "last_checked_at": "2026-07-05T08:00:00Z",
        "latency_ms": 1,
    },
]


def _stable_probe_all_connectors() -> list[dict[str, object]]:
    return list(STABLE_OK_CONNECTOR_RECORDS)


class StableConnectorProbePatch:
    """Patch every module-level import site for probe_all_connectors."""

    _TARGETS = (
        "app.connectors.summary.probe_all_connectors",
        "app.main.probe_all_connectors",
        "app.watch_summary.probe_all_connectors",
    )

    def __init__(self) -> None:
        self._patches: list[patch] = []

    def start(self) -> None:
        self._patches = []
        for target in self._TARGETS:
            patcher = patch(target, _stable_probe_all_connectors)
            patcher.start()
            self._patches.append(patcher)

    def stop(self) -> None:
        for item in reversed(self._patches):
            item.stop()
        self._patches.clear()


def patch_stable_connector_probes() -> StableConnectorProbePatch:
    return StableConnectorProbePatch()


def reset_watch_ephemeral_stores() -> None:
    from app.commands import store as command_store  # noqa: WPS433
    from app.delivery import store as delivery_store  # noqa: WPS433
    from app.events import store as event_store  # noqa: WPS433

    command_store.reset_store()
    delivery_store.reset_store()
    event_store.reset_store()
