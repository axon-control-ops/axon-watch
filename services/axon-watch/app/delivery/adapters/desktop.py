"""Desktop notification file adapter."""

from __future__ import annotations

import json

from app.delivery.config import desktop_notify_path
from app.signals.iso_time import utc_now_iso


def deliver_desktop(*, item: dict[str, object], signal_id: str) -> tuple[str, str, str]:
    payload = {
        "signal_id": signal_id,
        "title": str(item.get("title", "")).strip() or signal_id,
        "summary": str(item.get("summary", "")).strip(),
        "severity": str(item.get("severity", "info")).strip().lower() or "info",
        "attempted_at": utc_now_iso(),
    }
    path = desktop_notify_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, separators=(",", ":")) + "\n")
    except OSError as exc:
        return ("failed", str(exc), "desktop_notify_write_failed")
    return ("succeeded", "", "desktop_notification_recorded")
