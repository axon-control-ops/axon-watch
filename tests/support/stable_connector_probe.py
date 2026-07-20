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
        "health_url": "http://127.0.0.1:4173/api/health",
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
    {
        "connector_id": "cloudflare_tunnel",
        "display_name": "Cloudflare tunnel",
        "health_url": "https://example.test/",
        "required": True,
        "workspace_id": "workspace_axon_watch",
        "status": "ok",
        "detail": "reachable",
        "last_checked_at": "2026-07-05T08:00:00Z",
        "latency_ms": 1,
    },
]


def _stable_probe_all_connectors() -> list[dict[str, object]]:
    return list(STABLE_OK_CONNECTOR_RECORDS)


def _empty_monitor_records() -> list[dict[str, object]]:
    """Keep bootstrap inbox tests deterministic (no live DashPro monitor noise)."""
    return []


def _empty_email_inbox_items() -> list[dict[str, object]]:
    """Keep bootstrap inbox tests deterministic (no dev email stub noise)."""
    return []


class StableConnectorProbePatch:
    """Patch connector + monitor + email probe sites used by watch inbox assembly."""

    _CONNECTOR_TARGETS = (
        "app.connectors.summary.probe_all_connectors",
        "app.main.probe_all_connectors",
        "app.watch_summary.probe_all_connectors",
    )
    _MONITOR_TARGETS = (
        "app.signals.store.probe_monitor_records",
        "app.monitors.dashpro_monitor.probe_monitor_records",
    )
    _EMAIL_TARGETS = (
        "app.signals.store.email_inbox_items",
        "app.signals.email_signal.email_inbox_items",
    )

    def __init__(self) -> None:
        self._patches: list[patch] = []

    def start(self) -> None:
        self._patches = []
        for target in self._CONNECTOR_TARGETS:
            patcher = patch(target, _stable_probe_all_connectors)
            patcher.start()
            self._patches.append(patcher)
        for target in self._MONITOR_TARGETS:
            patcher = patch(target, _empty_monitor_records)
            patcher.start()
            self._patches.append(patcher)
        for target in self._EMAIL_TARGETS:
            patcher = patch(target, _empty_email_inbox_items)
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
    from app.connectors.summary import reset_connector_probe_cache  # noqa: WPS433
    from app.delivery import store as delivery_store  # noqa: WPS433
    from app.events import store as event_store  # noqa: WPS433
    from app.monitors.dashpro_monitor import reset_monitor_probe_cache  # noqa: WPS433
    from app.signals import suppression_store  # noqa: WPS433

    command_store.reset_store()
    delivery_store.reset_store()
    event_store.reset_store()
    suppression_store.reset_store()
    reset_monitor_probe_cache()
    reset_connector_probe_cache()
