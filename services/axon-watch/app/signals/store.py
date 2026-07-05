"""In-memory signal store for watch-produced canonical signals."""

from __future__ import annotations

from app.delivery.service import enrich_inbox_with_delivery
from app.signals.bootstrap_signal import bootstrap_inbox_item
from app.signals.connector_signal import connector_inbox_items
from app.signals.iso_time import utc_now_iso
from app.signals.ranking import rank_inbox_items
from app.signals.inbox_assembly import include_summary_degraded_signal
from app.signals.summary_degraded_signal import summary_degraded_inbox_item
from app.signals.suppression_store import is_signal_acknowledged
from app.signals.watch_rule import watch_rule_for_inbox_item


def get_inbox_snapshot(
    *,
    connector_records: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    items = [bootstrap_inbox_item()]
    if include_summary_degraded_signal(connector_records=connector_records):
        items.append(summary_degraded_inbox_item())
    if connector_records is not None:
        items.extend(connector_inbox_items(connector_records))

    ranked = rank_inbox_items(items)
    delivered = enrich_inbox_with_delivery(ranked)
    enriched = []
    for item in delivered:
        signal_id = str(item.get("signal_id", "")).strip()
        if signal_id and is_signal_acknowledged(signal_id):
            continue
        row = dict(item)
        row["watch_rule"] = watch_rule_for_inbox_item(row)
        enriched.append(row)
    return {
        "items": enriched,
        "count": len(enriched),
        "updated_at": utc_now_iso(),
    }
