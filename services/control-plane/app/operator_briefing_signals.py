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
