"""In-memory signal store for watch-produced canonical signals."""

from __future__ import annotations

from app.signals.bootstrap_signal import bootstrap_inbox_item
from app.signals.iso_time import utc_now_iso
from app.signals.ranking import rank_inbox_items
from app.signals.summary_degraded_signal import summary_degraded_inbox_item


def get_inbox_snapshot() -> dict[str, object]:
    items = rank_inbox_items(
        [
            bootstrap_inbox_item(),
            summary_degraded_inbox_item(),
        ]
    )
    return {
        "items": items,
        "count": len(items),
        "updated_at": utc_now_iso(),
    }
