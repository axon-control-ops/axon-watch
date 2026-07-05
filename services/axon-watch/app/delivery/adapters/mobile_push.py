"""Mobile push webhook delivery adapter."""

from __future__ import annotations

from urllib.error import HTTPError

from app.delivery.adapters.http_post import post_json
from app.delivery.config import optional_channel_urls
from app.signals.iso_time import utc_now_iso


def deliver_mobile_push(*, item: dict[str, object], signal_id: str) -> tuple[str, str, str]:
    url = optional_channel_urls().get("mobile_push")
    if not url:
        return ("failed", "AXON_WATCH_MOBILE_PUSH_URL is not configured", "channel_not_configured")

    payload = {
        "signal_id": signal_id,
        "title": str(item.get("title", "")).strip() or signal_id,
        "body": str(item.get("summary", "")).strip(),
        "severity": str(item.get("severity", "info")).strip().lower() or "info",
        "attempted_at": utc_now_iso(),
        "channel": "mobile_push",
    }
    try:
        post_json(url, payload)
    except HTTPError as exc:
        return ("failed", str(exc.reason or exc), "mobile_push_http_error")
    except (TimeoutError, ConnectionError) as exc:
        return ("failed", str(exc), "mobile_push_transport_error")
    except OSError as exc:
        return ("failed", str(exc), "mobile_push_transport_error")
    return ("succeeded", "", "mobile_push_delivered")
