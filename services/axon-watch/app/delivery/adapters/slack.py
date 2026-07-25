"""Slack incoming webhook delivery adapter."""

from __future__ import annotations

from urllib.error import HTTPError

from app.delivery.adapters.http_post import post_json
from app.delivery.config import optional_channel_urls


def deliver_slack(*, item: dict[str, object], signal_id: str) -> tuple[str, str, str]:
    url = optional_channel_urls().get("slack")
    if not url:
        return ("failed", "AXON_WATCH_SLACK_WEBHOOK_URL is not configured", "channel_not_configured")

    title = str(item.get("title", "")).strip() or signal_id
    summary = str(item.get("summary", "")).strip()
    severity = str(item.get("severity", "info")).strip().lower() or "info"
    text = f"[{severity}] {title}"
    if summary:
        text = f"{text}\n{summary}"

    payload = {"text": text, "signal_id": signal_id, "severity": severity}
    try:
        post_json(url, payload)
    except HTTPError as exc:
        return ("failed", str(exc.reason or exc), "slack_http_error")
    except (TimeoutError, ConnectionError) as exc:
        return ("failed", str(exc), "slack_transport_error")
    except OSError as exc:
        return ("failed", str(exc), "slack_transport_error")
    return ("succeeded", "", "slack_delivered")
