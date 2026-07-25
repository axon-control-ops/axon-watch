"""Registry dispatching delivery attempts to channel adapters."""

from __future__ import annotations

from collections.abc import Callable

from app.delivery.adapters import desktop, inbox, mobile_push, slack, webhook
from app.delivery.config import retry_max_attempts
from app.delivery.retry import deliver_with_retry

AdapterFn = Callable[..., tuple[str, str, str]]

_ADAPTERS: dict[str, AdapterFn] = {
    "inbox": inbox.deliver_inbox,
    "desktop": desktop.deliver_desktop,
    "webhook": webhook.deliver_webhook,
    "mobile_push": mobile_push.deliver_mobile_push,
    "slack": slack.deliver_slack,
}


def supported_channels() -> frozenset[str]:
    return frozenset(_ADAPTERS)


def attempt_channel_delivery(
    *,
    channel: str,
    item: dict[str, object],
    signal_id: str,
) -> tuple[str, str, str]:
    adapter = _ADAPTERS.get(channel.strip().lower())
    if adapter is None:
        return (
            "failed",
            f"Unsupported delivery channel: {channel}",
            "channel_unavailable",
        )

    return deliver_with_retry(
        lambda: adapter(item=item, signal_id=signal_id),
        max_attempts=retry_max_attempts(),
    )
