"""Best-effort live-event notification after material run lifecycle changes."""

from __future__ import annotations

from typing import Any


def notify_run_material_change(run_id: str, record: dict[str, Any]) -> None:
    try:
        from app.live_events import broadcast_material_change

        broadcast_material_change(receipt_id=str(record.get("run_id") or run_id))
    except Exception:
        pass
