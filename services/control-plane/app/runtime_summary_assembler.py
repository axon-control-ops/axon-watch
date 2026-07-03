"""Assemble the canonical RuntimeSummary DTO for the control-plane thin slice."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.adapters.watch_client import fetch_watch_inbox
from app.runs.service import list_active_runs, to_runtime_summary_active_run

_APP_VERSION = "0.1.0"
_PROCESS_STARTED_AT = time.monotonic()

WatchProbe = Callable[[], tuple[bool, str, str | None, str]]
WatchInboxFetcher = Callable[[], dict[str, object] | None]


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


def _runtime_identity() -> dict[str, object]:
    return {
        "provider_family": os.environ.get("AXON_WATCH_PROVIDER_FAMILY", "bootstrap"),
        "provider_name": os.environ.get("AXON_WATCH_PROVIDER_NAME", "Axon-Watch Bootstrap"),
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

    open_count = sum(1 for item in items if isinstance(item, dict) and item.get("status") == "open")
    critical_count = sum(
        1 for item in items if isinstance(item, dict) and item.get("severity") == "critical"
    )
    high_count = sum(1 for item in items if isinstance(item, dict) and item.get("severity") == "high")
    top_items = [item for item in items if isinstance(item, dict)][:1]

    return {
        "open_count": open_count,
        "critical_count": critical_count,
        "high_count": high_count,
        "top_items": top_items,
        "last_updated_at": str(watch_inbox.get("updated_at", generated_at)),
    }


def assemble_runtime_summary(
    *,
    watch_probe: WatchProbe | None = None,
    inbox_fetcher: WatchInboxFetcher | None = None,
) -> dict[str, object]:
    """Build a boot-safe runtime summary from live control-plane and watch probes."""
    probe = watch_probe or default_watch_probe
    inbox_loader = inbox_fetcher or fetch_watch_inbox
    generated_at = _utc_now_iso()
    watch_connected, watch_status, watch_degraded_reason, last_summary_at = probe()
    watch_inbox = inbox_loader() if watch_connected else None

    degraded_reasons: list[str] = []
    if not watch_connected and watch_degraded_reason:
        degraded_reasons.append(watch_degraded_reason)

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
        "runtime_identity": _runtime_identity(),
        "active_runs": [
            to_runtime_summary_active_run(record) for record in list_active_runs()
        ],
        "approvals": {
            "pending_count": 0,
            "highest_severity": None,
            "latest_approval_at": None,
        },
        "signals": _signals_summary_from_inbox(watch_inbox, generated_at),
        "capabilities": {
            "editor": True,
            "terminal": True,
            "browser_preview": True,
            "watch_connected": watch_connected,
            "approvals_enabled": True,
            "notifications_enabled": False,
        },
        "degraded": {
            "active": bool(degraded_reasons),
            "reasons": degraded_reasons,
        },
    }
