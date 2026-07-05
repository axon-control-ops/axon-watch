"""Attempt operator-attention delivery and enrich inbox items with receipt truth."""

from __future__ import annotations

import uuid

from app.delivery import policy, store
from app.events.store import append_event
from app.signals.iso_time import utc_now_iso


def _event_id_for_signal(signal_id: str) -> str:
    return f"event-delivery-{signal_id.strip()}"


def _simulate_channel_delivery(*, channel: str, item: dict[str, object]) -> tuple[str, str, str]:
    severity = str(item.get("severity", "info")).strip().lower() or "info"
    if channel == "inbox":
        return (
            "succeeded",
            "",
            "inbox_projection_available",
        )
    if channel == "desktop":
        return (
            "succeeded",
            "",
            "bootstrap_simulated_desktop_delivery",
        )
    return (
        "failed",
        f"Channel {channel} is not wired in bootstrap delivery slice.",
        "channel_unavailable",
    )


def _aggregate_delivery_state(receipts: list[dict[str, object]], attempted: bool) -> str:
    if not receipts and not attempted:
        return "not_required"
    if not receipts:
        return "pending"

    results = {str(receipt.get("result", "")).strip().lower() for receipt in receipts}
    if "failed" in results and "succeeded" not in results:
        return "failed"
    if "succeeded" in results:
        return "delivered"
    if attempted:
        return "attempted"
    return "pending"


def ensure_signal_delivery(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    signal_id = str(item.get("signal_id", "")).strip()
    if not signal_id:
        enriched["delivery_state"] = "not_required"
        return enriched

    if not policy.delivery_required_for_item(item):
        enriched.setdefault("delivery_state", "not_required")
        return enriched

    channels = policy.resolve_channels_for_item(item)
    if not channels:
        enriched["delivery_state"] = "not_required"
        return enriched

    event_id = _event_id_for_signal(signal_id)
    attempted_any = False
    signal_receipts = store.receipts_for_signal(signal_id)

    for channel in channels:
        if store.has_successful_delivery(signal_id=signal_id, channel=channel):
            continue

        attempted_any = True
        append_event(
            event_type="delivery_attempted",
            payload={
                "signal_id": signal_id,
                "event_id": event_id,
                "channel": channel,
            },
        )

        result, error, policy_reason = _simulate_channel_delivery(channel=channel, item=item)
        receipt = store.append_receipt(
            signal_id=signal_id,
            event_id=event_id,
            channel=channel,
            result=result,
            error=error,
            policy_reason=policy_reason,
        )
        signal_receipts.append(receipt)

        append_event(
            event_type="delivery_succeeded" if result == "succeeded" else "delivery_failed",
            payload={
                "signal_id": signal_id,
                "event_id": event_id,
                "channel": channel,
                "receipt_id": receipt["receipt_id"],
                "result": result,
                "error": error,
            },
        )

    all_receipts = store.receipts_for_signal(signal_id)
    enriched["delivery_state"] = _aggregate_delivery_state(all_receipts, attempted_any)
    enriched["delivery_receipt_count"] = len(all_receipts)
    if all_receipts:
        enriched["latest_receipt_id"] = str(all_receipts[-1].get("receipt_id", ""))
    enriched["updated_at"] = utc_now_iso()
    return enriched


def enrich_inbox_with_delivery(items: list[dict[str, object]]) -> list[dict[str, object]]:
    return [ensure_signal_delivery(item) for item in items]
