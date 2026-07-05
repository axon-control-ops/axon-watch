"""Generic webhook delivery adapter."""

from __future__ import annotations

from urllib.error import HTTPError

from app.delivery.adapters.http_post import post_json
from app.delivery.config import optional_channel_urls
from app.signals.iso_time import utc_now_iso


def deliver_webhook(*, item: dict[str, object], signal_id: str) -> tuple[str, str, str]:
    url = optional_channel_urls().get("webhook")
    if not url:
        return ("failed", "AXON_WATCH_DELIVERY_WEBHOOK_URL is not configured", "channel_not_configured")

    payload = {
        "signal_id": signal_id,
        "title": str(item.get("title", "")).strip() or signal_id,
        "summary": str(item.get("summary", "")).strip(),
        "severity": str(item.get("severity", "info")).strip().lower() or "info",
        "attempted_at": utc_now_iso(),
        "channel": "webhook",
    }
    try:
        post_json(url, payload)
    except HTTPError as exc:
        return ("failed", str(exc.reason or exc), "webhook_http_error")
    except (TimeoutError, ConnectionError) as exc:
        return ("failed", str(exc), "webhook_transport_error")
    except OSError as exc:
        return ("failed", str(exc), "webhook_transport_error")
    return ("succeeded", "", "webhook_delivered")
