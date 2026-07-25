"""Read-only operator data snapshot for watch persistence tables."""

from __future__ import annotations

from app.commands.store import list_commands
from app.delivery.store import delivery_summary, list_receipts
from app.events.store import events_summary, list_events
from app.signals.iso_time import utc_now_iso
from app.signals.suppression_store import list_acknowledgements


def operator_data_snapshot(*, limit: int = 50) -> dict[str, object]:
    max_limit = max(1, min(100, int(limit or 50)))
    commands = list_commands(limit=max_limit)
    events_page = list_events(limit=max_limit)
    receipts_page = list_receipts(limit=max_limit)
    suppressions = list_acknowledgements(limit=max_limit)
    events_meta = events_summary()
    receipts_meta = delivery_summary()

    return {
        "updated_at": utc_now_iso(),
        "tables": {
            "commands": {
                "total": commands["total"],
                "count": commands["count"],
                "items": commands["items"],
            },
            "events": {
                "total": int(events_meta.get("events_count", 0)),
                "count": events_page["count"],
                "items": events_page["items"],
            },
            "receipts": {
                "total": int(receipts_meta.get("receipts_count", 0)),
                "count": receipts_page["count"],
                "items": receipts_page["items"],
            },
            "suppressions": {
                "total": suppressions["total"],
                "count": suppressions["count"],
                "items": suppressions["items"],
            },
        },
    }
