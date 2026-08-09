"""Constitution health snapshot helpers.

These helpers turn the existing runtime summary into durable constitution
health records. They do not change runtime-summary behavior; callers opt in to
recording a snapshot when they need an evidence trail.
"""

from __future__ import annotations

from typing import Any

from app.persistence import constitution_registry_store as registry


def status_from_runtime_summary(runtime_summary: dict[str, Any]) -> str:
    degraded = runtime_summary.get("degraded")
    degraded = degraded if isinstance(degraded, dict) else {}
    control_plane = runtime_summary.get("control_plane")
    control_plane = control_plane if isinstance(control_plane, dict) else {}
    watch = runtime_summary.get("watch")
    watch = watch if isinstance(watch, dict) else {}

    if bool(degraded.get("active")):
        return "degraded"
    if control_plane and control_plane.get("ready") is False:
        return "degraded"
    if watch and watch.get("connected") is False:
        return "watch_unavailable"
    return "ready"


def health_signals_from_runtime_summary(runtime_summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "generated_at",
        "control_plane",
        "watch",
        "cli_runtime",
        "connectors",
        "approvals",
        "degraded",
        "active_runs",
    )
    return {key: runtime_summary[key] for key in keys if key in runtime_summary}


def record_runtime_summary_health_snapshot(
    runtime_summary: dict[str, Any],
    *,
    source: str = "runtime_summary",
) -> dict[str, Any]:
    return registry.record_health_snapshot(
        scope="platform",
        status=status_from_runtime_summary(runtime_summary),
        signals=health_signals_from_runtime_summary(runtime_summary),
        source=source,
    )
