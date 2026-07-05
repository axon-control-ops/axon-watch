"""Delivery channel resolution for watch-born operator attention signals."""

from __future__ import annotations

DEFAULT_SEVERITY_ROUTING: dict[str, list[str]] = {
    "info": ["inbox"],
    "warning": ["inbox"],
    "high": ["inbox", "desktop"],
    "critical": ["inbox", "desktop"],
}

SUPPORTED_CHANNELS = frozenset({"chat", "desktop", "mobile_push", "webhook", "slack", "inbox"})


def delivery_required_for_item(item: dict[str, object]) -> bool:
    explicit = str(item.get("delivery_state", "")).strip().lower()
    if explicit == "not_required":
        return False
    if explicit in {"delivered", "suppressed"}:
        return False
    severity = str(item.get("severity", "info")).strip().lower() or "info"
    return severity in {"warning", "high", "critical"}


def resolve_channels_for_item(item: dict[str, object]) -> list[str]:
    if not delivery_required_for_item(item):
        return []

    severity = str(item.get("severity", "info")).strip().lower() or "info"
    channels = DEFAULT_SEVERITY_ROUTING.get(severity, ["inbox"])
    return [channel for channel in channels if channel in SUPPORTED_CHANNELS]
