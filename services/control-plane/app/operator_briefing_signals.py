"""Shared briefing signal filtering for persona + conversation parity."""

from __future__ import annotations

from typing import Any

_BOOTSTRAP_SIGNAL_IDS = frozenset(
    {
        "signal_runtime_summary_degraded",
        "signal_watch_bootstrap_ready",
    }
)

_ACTIONABLE_SEVERITIES = frozenset({"critical", "high", "medium"})


def is_monitor_signal(signal: dict[str, Any]) -> bool:
    meta = signal.get("meta")
    if not isinstance(meta, dict):
        return False
    return str(meta.get("signal_family", "")).strip() == "child_project_monitor"


def filter_actionable_inbox_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if isinstance(item, dict) and not is_bootstrap_signal(item)]


def summarize_actionable_inbox(items: list[dict[str, Any]]) -> dict[str, Any]:
    actionable = filter_actionable_inbox_items(items)
    open_items = [item for item in actionable if item.get("status") == "open"]
    critical_count = sum(
        1 for item in open_items if str(item.get("severity", "")).strip() == "critical"
    )
    high_count = sum(
        1 for item in open_items if str(item.get("severity", "")).strip() == "high"
    )
    return {
        "open_count": len(open_items),
        "critical_count": critical_count,
        "high_count": high_count,
        "top_items": open_items[:1],
    }


def is_bootstrap_signal(signal: dict[str, Any]) -> bool:
    signal_id = str(signal.get("signal_id", "")).strip()
    title = str(signal.get("title", "")).lower()
    return signal_id in _BOOTSTRAP_SIGNAL_IDS or "bootstrap" in title


def first_actionable_signal(top_signals: object) -> dict[str, Any] | None:
    if not isinstance(top_signals, list):
        return None
    for item in top_signals:
        if not isinstance(item, dict):
            continue
        if is_bootstrap_signal(item):
            continue
        severity = str(item.get("severity", "")).strip().lower()
        if severity in _ACTIONABLE_SEVERITIES:
            return item
    return None
