"""Minimal in-memory signal store for the bootstrap thin slice."""

from __future__ import annotations

from app.signals.bootstrap_signal import bootstrap_inbox_item, utc_now_iso


def get_inbox_snapshot() -> dict[str, object]:
    item = bootstrap_inbox_item()
    return {
        "items": [item],
        "count": 1,
        "updated_at": utc_now_iso(),
    }
