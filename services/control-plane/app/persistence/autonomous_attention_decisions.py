"""Small persistence operations for autonomous attention decisions."""

from __future__ import annotations

from typing import Any


def supersede_pending_decision(receipt_id: str) -> dict[str, Any] | None:
    """Resolve a pending approval made obsolete by a verified completion."""
    from app.persistence import autonomous_attention_store as store

    cleaned = str(receipt_id or "").strip()
    if not cleaned:
        return None
    with store._managed_connection() as connection:
        store.ensure_autonomy_receipt_schema(connection)
        connection.execute(
            """
            UPDATE autonomy_attention_receipts
            SET status = 'resolved', resolution = 'superseded', resolved_at = ?
            WHERE receipt_id = ? AND status = 'pending'
            """,
            (store._utc_now_iso(), cleaned),
        )
        connection.commit()
    return store.get_receipt(cleaned)
