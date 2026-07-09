"""Actionable inbox filtering — hide bootstrap noise when live monitors fire."""

from __future__ import annotations

_BOOTSTRAP_SIGNAL_IDS = frozenset(
    {
        "signal_runtime_summary_degraded",
        "signal_watch_bootstrap_ready",
    }
)


def is_bootstrap_inbox_item(item: dict[str, object]) -> bool:
    signal_id = str(item.get("signal_id", "")).strip()
    title = str(item.get("title", "")).lower()
    return signal_id in _BOOTSTRAP_SIGNAL_IDS or "bootstrap" in title


def is_monitor_inbox_item(item: dict[str, object]) -> bool:
    meta = item.get("meta")
    if not isinstance(meta, dict):
        return False
    return str(meta.get("signal_family", "")).strip() == "child_project_monitor"


def filter_actionable_inbox_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    return [item for item in items if not is_bootstrap_inbox_item(item)]


def summarize_actionable_inbox(items: list[dict[str, object]]) -> dict[str, object]:
    actionable = filter_actionable_inbox_items(items)
    open_items = [
        item for item in actionable if isinstance(item, dict) and item.get("status") == "open"
    ]
    critical_count = sum(
        1 for item in open_items if str(item.get("severity", "")).strip() == "critical"
    )
    high_count = sum(
        1 for item in open_items if str(item.get("severity", "")).strip() == "high"
    )
    top_items = open_items[:1]
    return {
        "open_count": len(open_items),
        "critical_count": critical_count,
        "high_count": high_count,
        "top_items": top_items,
    }


def should_emit_bootstrap_signal(monitor_items: list[dict[str, object]]) -> bool:
    """Bootstrap is dev-only context — omit once a live child-project monitor fires."""
    return len(monitor_items) == 0
