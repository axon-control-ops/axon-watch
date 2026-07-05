"""In-memory delivery receipt store (bounded ring buffer)."""

from __future__ import annotations

import uuid
from collections import deque

from app.signals.iso_time import utc_now_iso

_MAX_RECEIPTS = 200
_RECEIPTS: deque[dict[str, object]] = deque(maxlen=_MAX_RECEIPTS)
_SUCCESS_KEYS: set[str] = set()


def reset_store() -> None:
    _RECEIPTS.clear()
    _SUCCESS_KEYS.clear()


def _dedupe_key(signal_id: str, channel: str) -> str:
    return f"{signal_id.strip()}::{channel.strip().lower()}"


def has_successful_delivery(*, signal_id: str, channel: str) -> bool:
    return _dedupe_key(signal_id, channel) in _SUCCESS_KEYS


def append_receipt(
    *,
    signal_id: str,
    event_id: str,
    channel: str,
    result: str,
    error: str = "",
    policy_reason: str = "",
) -> dict[str, object]:
    receipt = {
        "receipt_id": f"rcpt-{uuid.uuid4().hex[:16]}",
        "signal_id": signal_id.strip(),
        "event_id": event_id.strip(),
        "channel": channel.strip().lower(),
        "attempted_at": utc_now_iso(),
        "result": result.strip().lower(),
        "error": error.strip(),
        "policy_reason": policy_reason.strip(),
    }
    _RECEIPTS.append(receipt)
    if receipt["result"] == "succeeded":
        _SUCCESS_KEYS.add(_dedupe_key(signal_id, channel))
    return receipt


def list_receipts(*, limit: int = 20, cursor: str = "") -> dict[str, object]:
    max_limit = max(1, min(100, int(limit or 20)))
    items = list(_RECEIPTS)
    items.reverse()

    start_index = 0
    if cursor.strip():
        for index, item in enumerate(items):
            if item.get("receipt_id") == cursor.strip():
                start_index = index + 1
                break

    page = items[start_index : start_index + max_limit]
    next_cursor = ""
    if start_index + max_limit < len(items) and page:
        next_cursor = str(page[-1].get("receipt_id", ""))

    return {
        "items": page,
        "count": len(page),
        "next_cursor": next_cursor,
        "updated_at": utc_now_iso(),
    }


def receipts_for_signal(signal_id: str) -> list[dict[str, object]]:
    target = signal_id.strip()
    return [item for item in _RECEIPTS if str(item.get("signal_id", "")).strip() == target]


def delivery_summary() -> dict[str, object]:
    if not _RECEIPTS:
        return {
            "receipts_count": 0,
            "last_receipt_at": "",
            "last_receipt_result": "",
        }

    latest = _RECEIPTS[-1]
    return {
        "receipts_count": len(_RECEIPTS),
        "last_receipt_at": str(latest.get("attempted_at", "")),
        "last_receipt_result": str(latest.get("result", "")),
    }
