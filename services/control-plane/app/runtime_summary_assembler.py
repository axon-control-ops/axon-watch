"""Assemble the canonical RuntimeSummary DTO for the control-plane thin slice."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.adapters.watch_client import fetch_watch_inbox, fetch_watch_summary
from app.cli_runtime.catalog import runtime_identity_snapshot, runtime_status_snapshot
from app.cli_runtime.readiness import cli_runtime_degraded_reasons, summarize_cli_runtime_readiness
from app.operator_briefing_signals import summarize_actionable_inbox
from app.runs.service import (
    approval_summary,
    list_operator_facing_active_runs,
    to_runtime_summary_active_run,
)

_APP_VERSION = "0.1.0"
_PROCESS_STARTED_AT = time.monotonic()

WatchProbe = Callable[[], tuple[bool, str, str | None, str]]
WatchInboxFetcher = Callable[[], dict[str, object] | None]
WatchSummaryFetcher = Callable[[], dict[str, object] | None]


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _watch_base_url() -> str:
    return os.environ.get(
        "AXON_WATCH_WATCH_SERVICE_BASE_URL",
        "http://127.0.0.1:8788",
    ).rstrip("/")


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def default_watch_probe(timeout_seconds: float = 0.5) -> tuple[bool, str, str | None, str]:
    """Probe watch liveness and return connected, status, degraded_reason, last_summary_at."""
    generated_at = _utc_now_iso()
    url = f"{_watch_base_url()}/internal/watch/health"

    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return False, "unavailable", "watch probe failed", generated_at

    status = str(body.get("status", "unknown"))
    if status == "ok":
        return True, status, None, generated_at

    return False, status, "watch health returned non-ok status", generated_at


def _runtime_identity(*, allow_stale: bool = False) -> dict[str, object]:
    try:
        return runtime_identity_snapshot(allow_stale=allow_stale)
    except Exception:
        return {
            "provider_family": os.environ.get("AXON_WATCH_PROVIDER_FAMILY", "bootstrap"),
            "provider_name": os.environ.get("AXON_WATCH_PROVIDER_NAME", "Axon-X Bootstrap"),
            "model_name": os.environ.get("AXON_WATCH_MODEL_NAME", "bootstrap-model"),
            "mode_default": os.environ.get("AXON_WATCH_MODE_DEFAULT", "agent"),
            "tool_calling_supported": _env_bool("AXON_WATCH_TOOL_CALLING_SUPPORTED", False),
            "reasoning_supported": _env_bool("AXON_WATCH_REASONING_SUPPORTED", False),
        }


def _signals_summary_from_inbox(
    watch_inbox: dict[str, object] | None,
    generated_at: str,
) -> dict[str, object]:
    if not watch_inbox:
        return {
            "open_count": 0,
            "critical_count": 0,
            "high_count": 0,
            "top_items": [],
            "last_updated_at": generated_at,
        }

    items = watch_inbox.get("items", [])
    if not isinstance(items, list):
        items = []

    items = [item for item in items if isinstance(item, dict)]
    summary = summarize_actionable_inbox(items)

    return {
        "open_count": int(summary["open_count"]),
        "critical_count": int(summary["critical_count"]),
        "high_count": int(summary["high_count"]),
        "top_items": summary["top_items"],
        "last_updated_at": str(watch_inbox.get("updated_at", generated_at)),
    }


def _connectors_summary_from_watch(
    watch_summary: dict[str, object] | None,
    generated_at: str,
) -> dict[str, object]:
    if not watch_summary:
        return {
            "configured": 0,
            "ok": 0,
            "degraded": 0,
            "unavailable": 0,
            "required_unavailable": 0,
            "last_updated_at": generated_at,
        }

    connectors = watch_summary.get("connectors")
    if not isinstance(connectors, dict):
        connectors = {}

    return {
        "configured": int(connectors.get("configured", 0)),
        "ok": int(connectors.get("ok", 0)),
        "degraded": int(connectors.get("degraded", 0)),
        "unavailable": int(connectors.get("unavailable", 0)),
        "required_unavailable": int(connectors.get("required_unavailable", 0)),
        "last_updated_at": str(watch_summary.get("updated_at", generated_at)),
    }


def assemble_runtime_summary(
    *,
    watch_probe: WatchProbe | None = None,
    inbox_fetcher: WatchInboxFetcher | None = None,
    watch_summary_fetcher: WatchSummaryFetcher | None = None,
    light: bool = False,
) -> dict[str, object]:
    """Build a boot-safe runtime summary from live control-plane and watch probes."""
    probe = watch_probe or default_watch_probe
    inbox_loader = inbox_fetcher or fetch_watch_inbox
    summary_loader = watch_summary_fetcher or fetch_watch_summary
    generated_at = _utc_now_iso()
    watch_connected, watch_status, watch_degraded_reason, last_summary_at = probe()
    if light:
        # Presence ticks must not wait on watch summary or CLI auth rebuilds.
        watch_inbox = None
        watch_summary = None
        cli_status_snapshot = runtime_status_snapshot(allow_stale=True)
    else:
        watch_inbox = inbox_loader() if watch_connected else None
        watch_summary = summary_loader() if watch_connected else None
        cli_status_snapshot = runtime_status_snapshot(force_refresh=False)

    degraded_reasons: list[str] = []
    if not watch_connected and watch_degraded_reason:
        degraded_reasons.append(watch_degraded_reason)

    connectors = _connectors_summary_from_watch(watch_summary, generated_at)
    if watch_connected and connectors["required_unavailable"] > 0:
        degraded_reasons.append(
            f"{connectors['required_unavailable']} required connector(s) unavailable",
        )

    cli_runtime = summarize_cli_runtime_readiness(cli_status_snapshot)
    degraded_reasons.extend(cli_runtime_degraded_reasons(cli_status_snapshot))

    approvals = approval_summary()
    active_run_records = list_operator_facing_active_runs()
    active_runs = [to_runtime_summary_active_run(record) for record in active_run_records]

    return {
        "generated_at": generated_at,
        "control_plane": {
            "status": "ok",
            "version": _APP_VERSION,
            "uptime_seconds": int(time.monotonic() - _PROCESS_STARTED_AT),
            "ready": True,
        },
        "watch": {
            "status": watch_status,
            "connected": watch_connected,
            "last_summary_at": last_summary_at,
            "degraded_reason": watch_degraded_reason,
        },
        "runtime_identity": _runtime_identity(allow_stale=light),
        "active_runs": active_runs,
        "approvals": approvals,
        "signals": _signals_summary_from_inbox(watch_inbox, generated_at),
        "connectors": connectors,
        "cli_runtime": cli_runtime,
        "capabilities": {
            "editor": True,
            "terminal": True,
            "browser_preview": True,
            "watch_connected": watch_connected,
            "cli_dispatch_ready": bool(cli_runtime.get("dispatch_ready")),
            "approvals_enabled": True,
            "notifications_enabled": False,
        },
        "degraded": {
            "active": bool(degraded_reasons),
            "reasons": degraded_reasons,
        },
    }
