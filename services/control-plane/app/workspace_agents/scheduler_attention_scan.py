"""Periodic Full-autonomy attention scan used by the worker scheduler."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from app.persistence import autonomous_attention_store, operator_presence_settings_store

logger = logging.getLogger(__name__)

DEFAULT_AUTONOMY_SCAN_INTERVAL_SECONDS = 180.0


def autonomy_scan_interval_seconds() -> float:
    raw = os.environ.get("AXON_WATCH_AUTONOMY_SCAN_INTERVAL_SECONDS", "").strip()
    if not raw:
        return DEFAULT_AUTONOMY_SCAN_INTERVAL_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_AUTONOMY_SCAN_INTERVAL_SECONDS
    return max(45.0, value)


def run_scheduled_autonomous_attention_scan() -> dict[str, Any] | None:
    """Occasionally inspect configured workspaces while Full autonomy is effective."""
    from app.workspace_agents.scheduler import scheduler_enabled

    if not scheduler_enabled():
        return None
    settings = operator_presence_settings_store.load_settings()
    if str(settings.get("autonomy_mode") or "manual").strip().lower() != "full":
        return None

    last_scan = autonomous_attention_store.get_meta("last_scan") or {}
    scanned_at = str(last_scan.get("scanned_at") or "").strip()
    if scanned_at:
        try:
            previous = datetime.fromisoformat(scanned_at.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - previous).total_seconds()
            if age < autonomy_scan_interval_seconds():
                return None
        except ValueError:
            pass

    from app.workspace_agents.autonomous_attention import run_autonomous_attention_scan

    return run_autonomous_attention_scan(include_lead_checkin=False)


def run_due_attention_scan_and_log() -> None:
    result = run_scheduled_autonomous_attention_scan()
    if result:
        logger.info(
            "autonomous attention scan checked %s workspace(s), created %s task(s)",
            len(result.get("checked_workspaces") or []),
            len(result.get("created_tasks") or []),
        )
