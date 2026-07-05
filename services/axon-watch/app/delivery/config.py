"""Delivery channel configuration from environment."""

from __future__ import annotations

import os
from pathlib import Path


def state_dir() -> Path:
    raw = os.environ.get("AXON_WATCH_STATE_DIR", "./.local/state").strip() or "./.local/state"
    path = Path(raw)
    if path.is_absolute():
        return path
    repo_root = Path(__file__).resolve().parents[4]
    return (repo_root / path).resolve()


def desktop_notify_path() -> Path:
    configured = os.environ.get("AXON_WATCH_DESKTOP_NOTIFY_PATH", "").strip()
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else (state_dir() / path).resolve()
    return state_dir() / "desktop-notifications.jsonl"


def optional_channel_urls() -> dict[str, str | None]:
    return {
        "webhook": _clean_url("AXON_WATCH_DELIVERY_WEBHOOK_URL"),
        "mobile_push": _clean_url("AXON_WATCH_MOBILE_PUSH_URL"),
        "slack": _clean_url("AXON_WATCH_SLACK_WEBHOOK_URL"),
    }


def configured_optional_channels() -> list[str]:
    return [channel for channel, url in optional_channel_urls().items() if url]


def retry_max_attempts() -> int:
    raw = os.environ.get("AXON_WATCH_DELIVERY_RETRY_MAX", "3").strip()
    try:
        return max(1, min(5, int(raw)))
    except ValueError:
        return 3


def _clean_url(env_key: str) -> str | None:
    value = os.environ.get(env_key, "").strip()
    return value or None
